/**
 * Sample JavaScript code for testing the specification generator.
 * 
 * This module provides basic functionality for demonstration and testing purposes.
 * Includes ES6+ features, classes, async/await, and modern JavaScript patterns.
 */

import fs from 'fs';
import path from 'path';

/**
 * A sample user management class for testing.
 */
class UserManager {
    /**
     * Initialize the user manager.
     * @param {Object} config - Configuration object containing user management settings.
     */
    constructor(config = {}) {
        this.config = {
            maxUsers: 1000,
            sessionTimeout: 3600000, // 1 hour
            encryptionEnabled: true,
            ...config
        };
        this.users = new Map();
        this.sessions = new Map();
        this.eventListeners = new Map();
    }

    /**
     * Create a new user account.
     * @param {Object} userData - User data including username, email, and password.
     * @returns {Promise<Object>} Created user object or error.
     */
    async createUser(userData) {
        try {
            const { username, email, password } = userData;
            
            // Validate input
            if (!this._validateUserData(userData)) {
                throw new Error('Invalid user data provided');
            }
            
            // Check if user already exists
            if (this.users.has(username)) {
                throw new Error('User already exists');
            }
            
            // Check user limit
            if (this.users.size >= this.config.maxUsers) {
                throw new Error('Maximum user limit reached');
            }
            
            // Create user object
            const user = {
                id: this._generateUserId(),
                username,
                email,
                passwordHash: await this._hashPassword(password),
                createdAt: new Date(),
                lastLogin: null,
                isActive: true,
                permissions: ['read']
            };
            
            this.users.set(username, user);
            
            // Emit user created event
            this._emit('userCreated', { user });
            
            // Return user without password hash
            const { passwordHash, ...safeUser } = user;
            return safeUser;
            
        } catch (error) {
            console.error('Error creating user:', error.message);
            throw error;
        }
    }

    /**
     * Authenticate a user and create a session.
     * @param {string} username - Username for authentication.
     * @param {string} password - Password for authentication.
     * @returns {Promise<Object>} Session object with token.
     */
    async authenticateUser(username, password) {
        try {
            const user = this.users.get(username);
            
            if (!user) {
                throw new Error('User not found');
            }
            
            if (!user.isActive) {
                throw new Error('User account is deactivated');
            }
            
            const isValidPassword = await this._verifyPassword(password, user.passwordHash);
            if (!isValidPassword) {
                throw new Error('Invalid credentials');
            }
            
            // Create session
            const session = {
                id: this._generateSessionId(),
                userId: user.id,
                username: user.username,
                createdAt: new Date(),
                expiresAt: new Date(Date.now() + this.config.sessionTimeout),
                permissions: user.permissions
            };
            
            this.sessions.set(session.id, session);
            
            // Update last login
            user.lastLogin = new Date();
            
            // Emit login event
            this._emit('userLogin', { user, session });
            
            return {
                token: session.id,
                expiresAt: session.expiresAt,
                permissions: session.permissions
            };
            
        } catch (error) {
            console.error('Authentication failed:', error.message);
            throw error;
        }
    }

    /**
     * Get user by username.
     * @param {string} username - Username to search for.
     * @returns {Object|null} User object without sensitive data or null if not found.
     */
    getUser(username) {
        const user = this.users.get(username);
        
        if (!user) {
            return null;
        }
        
        const { passwordHash, ...safeUser } = user;
        return safeUser;
    }

    /**
     * Update user permissions.
     * @param {string} username - Username to update.
     * @param {Array<string>} permissions - New permissions array.
     * @returns {boolean} True if update successful, false otherwise.
     */
    updatePermissions(username, permissions) {
        const user = this.users.get(username);
        
        if (!user) {
            return false;
        }
        
        const validPermissions = ['read', 'write', 'admin', 'delete'];
        const filteredPermissions = permissions.filter(p => validPermissions.includes(p));
        
        user.permissions = filteredPermissions;
        
        // Emit permissions updated event
        this._emit('permissionsUpdated', { username, permissions: filteredPermissions });
        
        return true;
    }

    /**
     * Validate session token.
     * @param {string} token - Session token to validate.
     * @returns {Object|null} Session object if valid, null otherwise.
     */
    validateSession(token) {
        const session = this.sessions.get(token);
        
        if (!session) {
            return null;
        }
        
        // Check if session has expired
        if (new Date() > session.expiresAt) {
            this.sessions.delete(token);
            return null;
        }
        
        return session;
    }

    /**
     * Logout user by invalidating session.
     * @param {string} token - Session token to invalidate.
     * @returns {boolean} True if logout successful, false otherwise.
     */
    logout(token) {
        const session = this.sessions.get(token);
        
        if (!session) {
            return false;
        }
        
        this.sessions.delete(token);
        
        // Emit logout event
        this._emit('userLogout', { sessionId: token, username: session.username });
        
        return true;
    }

    /**
     * Get user statistics.
     * @returns {Object} Statistics about users and sessions.
     */
    getStatistics() {
        const activeUsers = Array.from(this.users.values()).filter(u => u.isActive).length;
        const activeSessions = Array.from(this.sessions.values()).filter(s => new Date() < s.expiresAt).length;
        
        return {
            totalUsers: this.users.size,
            activeUsers,
            activeSessions,
            maxUsers: this.config.maxUsers,
            utilizationRate: (this.users.size / this.config.maxUsers) * 100
        };
    }

    /**
     * Add event listener.
     * @param {string} event - Event name.
     * @param {Function} listener - Event listener function.
     */
    on(event, listener) {
        if (!this.eventListeners.has(event)) {
            this.eventListeners.set(event, []);
        }
        this.eventListeners.get(event).push(listener);
    }

    /**
     * Remove event listener.
     * @param {string} event - Event name.
     * @param {Function} listener - Event listener function to remove.
     */
    off(event, listener) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            const index = listeners.indexOf(listener);
            if (index > -1) {
                listeners.splice(index, 1);
            }
        }
    }

    // Private methods

    /**
     * Validate user data input.
     * @private
     * @param {Object} userData - User data to validate.
     * @returns {boolean} True if valid, false otherwise.
     */
    _validateUserData(userData) {
        const { username, email, password } = userData;
        
        if (!username || typeof username !== 'string' || username.length < 3) {
            return false;
        }
        
        if (!email || !this._isValidEmail(email)) {
            return false;
        }
        
        if (!password || password.length < 6) {
            return false;
        }
        
        return true;
    }

    /**
     * Validate email format.
     * @private
     * @param {string} email - Email to validate.
     * @returns {boolean} True if valid email format, false otherwise.
     */
    _isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Generate unique user ID.
     * @private
     * @returns {string} Unique user ID.
     */
    _generateUserId() {
        return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Generate unique session ID.
     * @private
     * @returns {string} Unique session ID.
     */
    _generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Hash password for storage.
     * @private
     * @param {string} password - Plain text password.
     * @returns {Promise<string>} Hashed password.
     */
    async _hashPassword(password) {
        // In real implementation, use bcrypt or similar
        // This is simplified for testing
        return `hashed_${password}_${Date.now()}`;
    }

    /**
     * Verify password against hash.
     * @private
     * @param {string} password - Plain text password.
     * @param {string} hash - Stored password hash.
     * @returns {Promise<boolean>} True if password matches, false otherwise.
     */
    async _verifyPassword(password, hash) {
        // In real implementation, use bcrypt.compare or similar
        // This is simplified for testing
        return hash.includes(password);
    }

    /**
     * Emit event to registered listeners.
     * @private
     * @param {string} event - Event name.
     * @param {Object} data - Event data.
     */
    _emit(event, data) {
        const listeners = this.eventListeners.get(event);
        if (listeners) {
            listeners.forEach(listener => {
                try {
                    listener(data);
                } catch (error) {
                    console.error('Error in event listener:', error);
                }
            });
        }
    }
}

/**
 * Utility functions for user management.
 */
export const UserUtils = {
    /**
     * Generate a secure random password.
     * @param {number} length - Password length (default: 12).
     * @returns {string} Generated password.
     */
    generatePassword(length = 12) {
        const charset = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
        let password = '';
        
        for (let i = 0; i < length; i++) {
            password += charset.charAt(Math.floor(Math.random() * charset.length));
        }
        
        return password;
    },

    /**
     * Check password strength.
     * @param {string} password - Password to check.
     * @returns {Object} Strength analysis with score and feedback.
     */
    checkPasswordStrength(password) {
        let score = 0;
        const feedback = [];
        
        if (password.length >= 8) score += 1;
        else feedback.push('Password should be at least 8 characters long');
        
        if (/[a-z]/.test(password)) score += 1;
        else feedback.push('Password should contain lowercase letters');
        
        if (/[A-Z]/.test(password)) score += 1;
        else feedback.push('Password should contain uppercase letters');
        
        if (/\d/.test(password)) score += 1;
        else feedback.push('Password should contain numbers');
        
        if (/[!@#$%^&*]/.test(password)) score += 1;
        else feedback.push('Password should contain special characters');
        
        const strength = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'][score];
        
        return { score, strength, feedback };
    },

    /**
     * Format user data for display.
     * @param {Object} user - User object.
     * @returns {string} Formatted user string.
     */
    formatUser(user) {
        return `${user.username} (${user.email}) - Created: ${user.createdAt.toLocaleDateString()}`;
    }
};

/**
 * Export the UserManager class as default.
 */
export default UserManager;

/**
 * Named exports for additional functionality.
 */
export { UserManager, UserUtils };