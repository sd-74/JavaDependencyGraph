from collections import defaultdict, Counter
from pathlib import Path

# canon ids
def module_id(pkg):           return f"module:{pkg}"
def class_id(fqn):            return f"class:{fqn}"
def interface_id(fqn):        return f"interface:{fqn}"
def method_id(owner,name,sig):return f"method:{owner}#{name}({sig})"
def ctor_id(owner,sig=""):    return f"constructor:{owner}::<init>({sig})"

class Analyzer:
    def __init__(self):
        self.files = []           # raw file summaries from parser
        self.nodes = []           # [{id,label}]
        self.edges = []           # [{src,label,dst,resolved}]
        self._edge_set = set()

        # symbol tables
        self.classes_by_fqn = {}  # fqn -> {node_id, pkg, name, extends[]}
        self.methods_by_owner_sig = {}  # "owner#name(sig)" -> node_id
        self.methods_index = {}    # (owner,name,arity) -> method node
        self.parents = {}          # child_fqn -> base_fqn

    def add_edge(self, src, label, dst, resolved=True):
        key = (src,label,dst)
        if key in self._edge_set: return
        self._edge_set.add(key)
        self.edges.append({"src":src,"label":label,"dst":dst,"resolved":bool(resolved)})

    # ---- stage 1: add module/class/interface/method nodes and ParentOf/ChildOf ----
    def stage1_add_syntactic(self):
        for f in self.files:
            file_path = Path(f["path"])
            # Get relative path for metadata
            try:
                # Try to get relative path from a common root
                rel_path = str(file_path)
            except:
                rel_path = str(file_path)
            
            # Read source code once per file
            source_code = file_path.read_text(encoding="utf-8")
            
            sym = f["symbols"]
            pkg = sym["package"]
            mid = module_id(pkg)
            self.nodes.append({
                "id": mid, 
                "label": f"Module: {pkg}",
                "metadata": {
                    "file_path": rel_path,
                    "line_range": [1, len(source_code.splitlines())]
                }
            })
            
            for t in sym["types"]:
                cid = t["node_id"]
                fqn = t["fqn"]
                line_range = t.get("line_range", [1, 1])
                byte_range = t.get("range", [0, 0])
                
                # Extract source code for class/interface
                class_source = source_code[byte_range[0]:byte_range[1]] if byte_range else ""
                
                if t.get("is_interface", False):
                    self.nodes.append({
                        "id": cid, 
                        "label": f"Interface: {t['name']}",
                        "metadata": {
                            "file_path": rel_path,
                            "line_range": line_range,
                            "source_code": class_source,
                            "owner_fqn": fqn,
                            "is_interface": True
                        }
                    })
                else:
                    self.nodes.append({
                        "id": cid, 
                        "label": f"Class: {t['name']}",
                        "metadata": {
                            "file_path": rel_path,
                            "line_range": line_range,
                            "source_code": class_source,
                            "owner_fqn": fqn,
                            "is_interface": False
                        }
                    })
                self.add_edge(mid, "ParentOf", cid)
                self.add_edge(cid, "ChildOf", mid)
            
            for m in sym["methods"]:
                mid_m = m["node_id"]
                line_range = m.get("line_range", [1, 1])
                byte_range = m.get("range", [0, 0])
                
                # Extract source code for method
                method_source = source_code[byte_range[0]:byte_range[1]] if byte_range else ""
                
                # Owner could be class or interface - lookup from current file's types
                owner_fqn = m["owner_fqn"]
                # Find the owner type in the current file's symbols
                owner_info = None
                for t in sym["types"]:
                    if t["fqn"] == owner_fqn:
                        owner_info = t
                        break
                
                self.nodes.append({
                    "id": mid_m, 
                    "label": f"Method: {m['name']}",
                    "metadata": {
                        "file_path": rel_path,
                        "line_range": line_range,
                        "source_code": method_source,
                        "owner_fqn": owner_fqn,
                        "return_type": m.get("return_type"),
                        "params": m.get("params", [])
                    }
                })
                
                if owner_info and owner_info.get("is_interface", False):
                    owner = interface_id(owner_fqn)
                else:
                    owner = class_id(owner_fqn)
                self.add_edge(owner, "ParentOf", mid_m)
                self.add_edge(mid_m, "ChildOf", owner)

    # ---- stage 2: build symbol tables ----
    def stage2_build_symbols(self):
        for f in self.files:
            sym = f["symbols"]
            pkg = sym["package"]
            for t in sym["types"]:
                self.classes_by_fqn[t["fqn"]] = {
                    "node_id": t["node_id"], "pkg": pkg, "name": t["name"], 
                    "extends": t["extends"], "implements": t.get("implements", []),
                    "is_interface": t.get("is_interface", False)
                }
            for m in sym["methods"]:
                key = m["sig"]         # "owner#name(sig)"
                self.methods_by_owner_sig[key] = m["node_id"]
                # arity index
                owner, rest = key.split("#",1)
                name, sig = rest.split("(",1)
                sig = sig.rstrip(")")
                arity = 0 if sig == "" else len([p for p in sig.split(",") if p])
                self.methods_index[(owner, name, arity)] = m["node_id"]

    # ---- stage 3: CHA + overrides ----
    def stage3_cha_and_overrides(self):
        # CHA
        for fqn, info in self.classes_by_fqn.items():
            for base_simple in info["extends"]:
                base_fqn = self._resolve_simple(base_simple, info["pkg"])
                if not base_fqn: continue
                self.parents[fqn] = base_fqn
                self.add_edge(class_id(base_fqn), "BaseClassOf", class_id(fqn))
                self.add_edge(class_id(fqn), "DerivedClassOf", class_id(base_fqn))
        # overrides (name+arity match up the chain)
        for key, mid in self.methods_by_owner_sig.items():
            owner, rest = key.split("#",1)
            name, sig = rest.split("(",1)
            sig = sig.rstrip(")")
            arity = 0 if sig == "" else len([p for p in sig.split(",") if p])
            for anc in self._ancestors(owner):
                cand = self.methods_index.get((anc, name, arity))
                if cand:
                    self.add_edge(mid, "Overrides", cand)
                    self.add_edge(cand, "OverriddenBy", mid)
                    break
            # Check implemented interfaces for overrides
            owner_info = self.classes_by_fqn.get(owner)
            if owner_info and not owner_info.get("is_interface", False):
                for interface_simple in owner_info.get("implements", []):
                    interface_fqn = self._resolve_simple(interface_simple, owner_info["pkg"])
                    if interface_fqn:
                        cand = self.methods_index.get((interface_fqn, name, arity))
                        if cand:
                            self.add_edge(mid, "Overrides", cand)
                            self.add_edge(cand, "OverriddenBy", mid)
                            break

    # ---- stage 3b: implements relationships ----
    def stage3b_implements(self):
        """Process implements relationships (class -> interface)"""
        for fqn, info in self.classes_by_fqn.items():
            if info.get("is_interface", False):
                continue
            for interface_simple in info.get("implements", []):
                interface_fqn = self._resolve_simple(interface_simple, info["pkg"])
                if not interface_fqn:
                    continue
                class_node = class_id(fqn)
                interface_node = interface_id(interface_fqn)
                self.add_edge(class_node, "Implements", interface_node)
                self.add_edge(interface_node, "ImplementedBy", class_node)

    # ---- stage 4: resolve Calls/Instantiates ----
    def stage4_calls_and_news(self):
        for f in self.files:
            sym = f["symbols"]
            pkg = sym["package"]
            # group by owner
            per_owner = defaultdict(list)
            for s in sym["stmts"]:
                per_owner[s["owner_method"]].append(s)
            for owner_id, stmts in per_owner.items():
                owner_fqn = owner_id[len("method:"):].split("#",1)[0]
                locals_map = {"this": owner_fqn}
                base = self.parents.get(owner_fqn)
                if base: locals_map["super"] = base
                # first pass: locals
                for s in sorted(stmts, key=lambda x: x["range"][0]):
                    if s["kind"] == "local":
                        t = s["parts"]["type"]
                        fqn = self._resolve_simple(t, pkg)
                        if fqn: locals_map[s["parts"]["name"]] = fqn
                # second pass: news + calls
                for s in sorted(stmts, key=lambda x: x["range"][0]):
                    if s["kind"] == "new":
                        fqn = self._resolve_simple(s["parts"]["type"], pkg)
                        if not fqn: continue
                        tgt = class_id(fqn)  # Point to class instead of constructor
                        self.add_edge(owner_id, "Instantiates", tgt)
                        self.add_edge(tgt, "InstantiatedBy", owner_id)
                    elif s["kind"] == "call":
                        recv = s["parts"]["recv"]
                        name = s["parts"]["name"]
                        arity = len(s["parts"]["args"])
                        recv_fqn = None
                        if recv in (None, "", "this"):
                            recv_fqn = owner_fqn
                        elif recv == "super":
                            recv_fqn = self.parents.get(owner_fqn)
                        elif recv in locals_map:
                            recv_fqn = locals_map[recv]
                        else:
                            recv_fqn = self._resolve_simple(recv, pkg)  # maybe static
                        if not recv_fqn: continue
                        tgt = self._lookup_method(recv_fqn, name, arity)
                        if tgt:
                            self.add_edge(owner_id, "Calls", tgt)
                            self.add_edge(tgt, "CalledBy", owner_id)

    # ---- helpers ----
    def _resolve_simple(self, simple, pkg):
        # exact match by package first
        cand = f"{pkg}.{simple}" if pkg and not simple.startswith(pkg) else simple
        if cand in self.classes_by_fqn: return cand
        # fallback: suffix match
        for fqn in self.classes_by_fqn.keys():
            if fqn.endswith("." + simple) or fqn == simple: return fqn
        return None

    # ---- stage 5: resolve Uses/UsedBy (type dependencies) ----
    def stage5_type_usage(self):
        """
        Extract Uses/UsedBy edges for type dependencies from:
        - Local variable declarations (existing stmts)
        - Method parameter types
        - Method return types
        - Field types
        Only track types defined in this repo (ignore primitives/JDK types).
        """
        for f in self.files:
            sym = f["symbols"]
            pkg = sym["package"]

            # 1) Local variable types
            for s in sym["stmts"]:
                if s["kind"] == "local":
                    owner_method = s["owner_method"]
                    var_type = s["parts"].get("type")
                    if not var_type:
                        continue
                    clean = var_type.replace("[]", "").strip()
                    type_fqn = self._resolve_simple(clean, pkg)
                    if type_fqn and type_fqn in self.classes_by_fqn:
                        type_info = self.classes_by_fqn[type_fqn]
                        if type_info.get("is_interface", False):
                            cls_node = interface_id(type_fqn)
                        else:
                            cls_node = class_id(type_fqn)
                        self.add_edge(owner_method, "Uses", cls_node)
                        self.add_edge(cls_node, "UsedBy", owner_method)

            # 2) Method parameter and return types
            for m in sym["methods"]:
                method_node = m["node_id"]
                # params
                for ptype in m.get("params", []) or []:
                    clean = ptype.replace("[]", "").strip()
                    type_fqn = self._resolve_simple(clean, pkg)
                    if type_fqn and type_fqn in self.classes_by_fqn:
                        type_info = self.classes_by_fqn[type_fqn]
                        if type_info.get("is_interface", False):
                            cls_node = interface_id(type_fqn)
                        else:
                            cls_node = class_id(type_fqn)
                        self.add_edge(method_node, "Uses", cls_node)
                        self.add_edge(cls_node, "UsedBy", method_node)
                # return type
                rtype = m.get("return_type")
                if rtype:
                    clean = rtype.replace("[]", "").strip()
                    type_fqn = self._resolve_simple(clean, pkg)
                    if type_fqn and type_fqn in self.classes_by_fqn:
                        type_info = self.classes_by_fqn[type_fqn]
                        if type_info.get("is_interface", False):
                            cls_node = interface_id(type_fqn)
                        else:
                            cls_node = class_id(type_fqn)
                        self.add_edge(method_node, "Uses", cls_node)
                        self.add_edge(cls_node, "UsedBy", method_node)

            # 3) Field types (per class)
            for field in sym.get("fields", []) or []:
                owner_class = class_id(field["owner_fqn"]) if field.get("owner_fqn") else None
                ftype = field.get("type")
                if not owner_class or not ftype:
                    continue
                clean = ftype.replace("[]", "").strip()
                type_fqn = self._resolve_simple(clean, pkg)
                if type_fqn and type_fqn in self.classes_by_fqn:
                    type_info = self.classes_by_fqn[type_fqn]
                    if type_info.get("is_interface", False):
                        cls_node = interface_id(type_fqn)
                    else:
                        cls_node = class_id(type_fqn)
                    self.add_edge(owner_class, "Uses", cls_node)
                    self.add_edge(cls_node, "UsedBy", owner_class)

    def _ancestors(self, fqn):
        cur = self.parents.get(fqn)
        while cur:
            yield cur
            cur = self.parents.get(cur)

    def _lookup_method(self, owner_fqn, name, arity):
        node = self.methods_index.get((owner_fqn, name, arity))
        if node: return node
        for anc in self._ancestors(owner_fqn):
            node = self.methods_index.get((anc, name, arity))
            if node: return node
        return None
