from tree_sitter import Language, Parser
from pathlib import Path
import json, sys

_LANG_SO = Path("build/languages.so")
_JAVA_REPO = Path("build/tree-sitter-java")

def get_java_parser() -> Parser:
    if not _LANG_SO.exists():
        _JAVA_REPO.mkdir(parents=True, exist_ok=True)
        # shallow clone if not present
        import subprocess
        if not (_JAVA_REPO / ".git").exists():
            subprocess.run(["git", "clone", "--depth", "1",
                            "https://github.com/tree-sitter/tree-sitter-java",
                            str(_JAVA_REPO)], check=True)
        Language.build_library(str(_LANG_SO), [str(_JAVA_REPO)])

    lang = Language(str(_LANG_SO), "java")
    p = Parser()
    p.set_language(lang)
    return p

def slice_text(src: bytes, node):
    return src[node.start_byte:node.end_byte].decode("utf-8")

def byte_to_line(src: bytes, byte_pos: int) -> int:
    """Convert byte position to 1-indexed line number"""
    return src[:byte_pos].count(b'\n') + 1

def parse_file(path: str | Path):
    path = Path(path)
    src_b = path.read_bytes()
    parser = get_java_parser()
    tree = parser.parse(src_b)
    root = tree.root_node

    pkg = None
    types = []
    methods = []
    fields = []
    stmts = []  # call/new/fieldref/local

    # walk top-level
    for ch in root.children:
        if ch.type == "package_declaration":
            name = ch.child_by_field_name("name")
            if name:
                pkg = slice_text(src_b, name).strip()
            else:
                # Try to find the package name in children
                for child in ch.children:
                    if child.type == "scoped_identifier":
                        pkg = slice_text(src_b, child).strip()
                        break
        if ch.type in ["class_declaration", "interface_declaration"]:
            is_interface = (ch.type == "interface_declaration")
            cls = ch
            name = cls.child_by_field_name("name")
            cls_name = slice_text(src_b, name)
            fqn = f"{pkg}.{cls_name}" if pkg else cls_name

            # super (for classes) or extends (for interfaces)
            extends = []
            sc = cls.child_by_field_name("superclass")
            if sc:
                extends.append(slice_text(src_b, sc).replace("extends", "").strip())
            
            # implements (for classes)
            implements = []
            if not is_interface:
                impls = cls.child_by_field_name("interfaces")
                if impls:
                    # The interfaces field contains a type_list with type_identifier nodes
                    for impl in impls.children:
                        if impl.type == "type_list":
                            for type_node in impl.children:
                                if type_node.type == "type_identifier":
                                    implements.append(slice_text(src_b, type_node).strip())
                        elif impl.type == "type_identifier":
                            implements.append(slice_text(src_b, impl).strip())

            types.append({
                "kind": "interface" if is_interface else "class",
                "name": cls_name,
                "fqn": fqn,
                "extends": extends,
                "implements": implements,
                "is_interface": is_interface,
                "range": [cls.start_byte, cls.end_byte],
                "line_range": [byte_to_line(src_b, cls.start_byte), byte_to_line(src_b, cls.end_byte)],
                "node_id": f"interface:{fqn}" if is_interface else f"class:{fqn}"
            })

            # members
            body = cls.child_by_field_name("body")
            if not body: continue
            for mem in body.children:
                if mem.type == "method_declaration":
                    mname = slice_text(src_b, mem.child_by_field_name("name"))
                    params = mem.child_by_field_name("parameters")
                    # collect parameter types
                    ps = []
                    if params:
                        for p in [c for c in params.children if c.type == "formal_parameter"]:
                            t = p.child_by_field_name("type")
                            if t:
                                ps.append(slice_text(src_b, t).strip())
                    # return type (may be None for constructors)
                    rtype_node = mem.child_by_field_name("type")
                    return_type = slice_text(src_b, rtype_node).strip() if rtype_node else None
                    sig = ",".join(ps)
                    mid = f"method:{fqn}#{mname}({sig})"
                    methods.append({
                        "owner_fqn": fqn,
                        "name": mname,
                        "sig": f"{fqn}#{mname}({sig})",
                        "range": [mem.start_byte, mem.end_byte],
                        "line_range": [byte_to_line(src_b, mem.start_byte), byte_to_line(src_b, mem.end_byte)],
                        "node_id": mid,
                        "params": ps,
                        "return_type": return_type
                    })
                    # collect simple stmts inside body
                    block = mem.child_by_field_name("body")
                    if block:
                        _collect_stmts(src_b, block, owner=mid, pkg=pkg, stmts=stmts)
                elif mem.type == "field_declaration":
                    # capture field declarations for type usage
                    ftype = mem.child_by_field_name("type")
                    # variable_declarator(s) can be multiple per declaration
                    decls = [c for c in mem.children if c.type == "variable_declarator"]
                    for d in decls:
                        fname_node = d.child_by_field_name("name")
                        if not fname_node: continue
                        fields.append({
                            "owner_fqn": fqn,
                            "name": slice_text(src_b, fname_node),
                            "type": slice_text(src_b, ftype).strip() if ftype else None,
                            "node_id": f"field:{fqn}#{slice_text(src_b, fname_node)}"
                        })

    return {
        "path": str(path),
        "symbols": {
            "package": pkg or "<default>",
            "types": types,
            "methods": methods,
            "fields": fields,
            "stmts": stmts,
        }
    }

def _collect_stmts(src_b, node, owner, pkg, stmts):
    # walk subtree recursively to find method_invocation, object_creation, local vars
    stack = [node]
    while stack:
        n = stack.pop()
        for c in n.children: stack.append(c)

        if n.type == "local_variable_declaration":
            t = n.child_by_field_name("type")
            decls = [c for c in n.children if c.type == "variable_declarator"]
            for d in decls:
                name = slice_text(src_b, d.child_by_field_name("name"))
                stmts.append({
                    "kind": "local",
                    "owner_method": owner,
                    "parts": {"name": name, "type": slice_text(src_b, t).strip()},
                    "range": [n.start_byte, n.end_byte]
                })
        elif n.type == "object_creation_expression":
            t = n.child_by_field_name("type")
            stmts.append({
                "kind": "new",
                "owner_method": owner,
                "parts": {"type": slice_text(src_b, t).strip()},
                "range": [n.start_byte, n.end_byte]
            })
        elif n.type == "method_invocation":
            obj = n.child_by_field_name("object")
            name = n.child_by_field_name("name")
            args = n.child_by_field_name("arguments")
            arglist = []
            if args:
                # count args quickly (text; we only need arity)
                txt = slice_text(src_b, args).strip()
                inner = txt[1:-1]
                arglist = [a for a in [x.strip() for x in inner.split(",")] if a] if inner else []
            recv = None
            if obj:
                recv = slice_text(src_b, obj).strip()
            stmts.append({
                "kind": "call",
                "owner_method": owner,
                "parts": {"recv": recv, "name": slice_text(src_b, name), "args": arglist},
                "range": [n.start_byte, n.end_byte]
            })
