package com.example.service;

import com.example.repository.UserRepository;
import com.example.email.EmailService;

public class UserService {
    private UserRepository userRepository;
    private EmailService emailService;
    
    public UserService() {
        this.userRepository = new UserRepository();
        this.emailService = new EmailService();
    }
    
    public User createUser(String name, String email) {
        User user = new User(name, email);
        userRepository.save(user);
        emailService.sendWelcomeEmail(user.getEmail());
        return user;
    }
    
    public User updateUser(Long id, String name, String email) {
        User user = userRepository.findById(id);
        if (user != null) {
            user.setName(name);
            user.setEmail(email);
            userRepository.save(user);
            emailService.sendUpdateEmail(user.getEmail());
        }
        return user;
    }
    
    public void deleteUser(Long id) {
        User user = userRepository.findById(id);
        if (user != null) {
            userRepository.delete(user);
            emailService.sendGoodbyeEmail(user.getEmail());
        }
    }
}