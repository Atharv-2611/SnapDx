// SnapDx Main JavaScript File
// Common utilities and functionality for the SnapDx application

// Global configuration
const SnapDxConfig = {
    apiBaseUrl: 'https://api.snapdx.com',
    version: '1.0.0',
    debug: false
};

// Utility functions
const SnapDxUtils = {
    // Logging utility
    log: function(message, type = 'info') {
        if (SnapDxConfig.debug) {
            const timestamp = new Date().toISOString();
            console.log(`[SnapDx ${timestamp}] ${type.toUpperCase()}: ${message}`);
        }
    },

    // Error handling utility
    handleError: function(error, context = '') {
        SnapDxUtils.log(`Error in ${context}: ${error.message}`, 'error');
        console.error(error);
        
        // Show user-friendly error message
        this.showNotification('An error occurred. Please try again.', 'error');
    },

    // Show notification
    showNotification: function(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-md shadow-lg max-w-sm transform transition-all duration-300 translate-x-full`;
        
        // Set notification styles based on type
        switch (type) {
            case 'success':
                notification.classList.add('bg-green-500', 'text-white');
                break;
            case 'error':
                notification.classList.add('bg-red-500', 'text-white');
                break;
            case 'warning':
                notification.classList.add('bg-yellow-500', 'text-white');
                break;
            default:
                notification.classList.add('bg-blue-500', 'text-white');
        }
        
        notification.innerHTML = `
            <div class="flex items-center">
                <span class="flex-1">${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white hover:text-gray-200">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after duration
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, duration);
    },

    // Format date
    formatDate: function(date) {
        return new Date(date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Format time
    formatTime: function(date) {
        return new Date(date).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Validate email
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validate phone number
    isValidPhone: function(phone) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        return phoneRegex.test(phone.replace(/\s/g, ''));
    },

    // Generate random ID
    generateId: function() {
        return Math.random().toString(36).substr(2, 9);
    },

    // Local storage utilities
    storage: {
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (error) {
                SnapDxUtils.handleError(error, 'localStorage.set');
            }
        },
        
        get: function(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                SnapDxUtils.handleError(error, 'localStorage.get');
                return defaultValue;
            }
        },
        
        remove: function(key) {
            try {
                localStorage.removeItem(key);
            } catch (error) {
                SnapDxUtils.handleError(error, 'localStorage.remove');
            }
        },
        
        clear: function() {
            try {
                localStorage.clear();
            } catch (error) {
                SnapDxUtils.handleError(error, 'localStorage.clear');
            }
        }
    }
};

// API utilities
const SnapDxAPI = {
    // Base request function
    request: async function(endpoint, options = {}) {
        const url = `${SnapDxConfig.apiBaseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${SnapDxUtils.storage.get('authToken')}`
            }
        };
        
        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            SnapDxUtils.handleError(error, `API request to ${endpoint}`);
            throw error;
        }
    },

    // GET request
    get: function(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    // POST request
    post: function(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // PUT request
    put: function(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // DELETE request
    delete: function(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
};

// Authentication utilities
const SnapDxAuth = {
    // Check if user is authenticated
    isAuthenticated: function() {
        const token = SnapDxUtils.storage.get('authToken');
        const user = SnapDxUtils.storage.get('user');
        return !!(token && user);
    },

    // Get current user
    getCurrentUser: function() {
        return SnapDxUtils.storage.get('user');
    },

    // Login
    login: async function(email, password, role) {
        try {
            const response = await SnapDxAPI.post('/auth/login', {
                email,
                password,
                role
            });
            
            if (response.token) {
                SnapDxUtils.storage.set('authToken', response.token);
                SnapDxUtils.storage.set('user', response.user);
                SnapDxUtils.storage.set('userRole', role);
                
                SnapDxUtils.showNotification('Login successful!', 'success');
                return response;
            }
        } catch (error) {
            SnapDxUtils.handleError(error, 'login');
            throw error;
        }
    },

    // Logout
    logout: function() {
        SnapDxUtils.storage.remove('authToken');
        SnapDxUtils.storage.remove('user');
        SnapDxUtils.storage.remove('userRole');
        
        SnapDxUtils.showNotification('Logged out successfully', 'info');
        
        // Redirect to login page
        window.location.href = '/login.html';
    },

    // Register
    register: async function(userData) {
        try {
            const response = await SnapDxAPI.post('/auth/register', userData);
            SnapDxUtils.showNotification('Registration successful!', 'success');
            return response;
        } catch (error) {
            SnapDxUtils.handleError(error, 'register');
            throw error;
        }
    }
};

// UI utilities
const SnapDxUI = {
    // Show loading spinner
    showLoading: function(element, text = 'Loading...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            element.innerHTML = `
                <div class="flex items-center justify-center p-4">
                    <div class="spinner spinner-md mr-3"></div>
                    <span class="text-gray-600">${text}</span>
                </div>
            `;
        }
    },

    // Hide loading spinner
    hideLoading: function(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            element.innerHTML = '';
        }
    },

    // Show modal
    showModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    },

    // Hide modal
    hideModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }
    },

    // Toggle sidebar
    toggleSidebar: function() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('hidden');
        }
    },

    // Smooth scroll to element
    scrollTo: function(element, offset = 0) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            const elementPosition = element.offsetTop - offset;
            window.scrollTo({
                top: elementPosition,
                behavior: 'smooth'
            });
        }
    },

    // Copy to clipboard
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            SnapDxUtils.showNotification('Copied to clipboard!', 'success');
        } catch (error) {
            SnapDxUtils.handleError(error, 'copyToClipboard');
        }
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// Form utilities
const SnapDxForms = {
    // Validate form
    validateForm: function(formElement) {
        const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                this.showFieldError(input, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(input);
            }
        });
        
        return isValid;
    },

    // Show field error
    showFieldError: function(field, message) {
        field.classList.add('border-red-500');
        
        let errorElement = field.parentElement.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'field-error text-red-500 text-sm mt-1';
            field.parentElement.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
    },

    // Clear field error
    clearFieldError: function(field) {
        field.classList.remove('border-red-500');
        
        const errorElement = field.parentElement.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    },

    // Reset form
    resetForm: function(formElement) {
        formElement.reset();
        const errorElements = formElement.querySelectorAll('.field-error');
        errorElements.forEach(element => element.remove());
        
        const inputs = formElement.querySelectorAll('input, select, textarea');
        inputs.forEach(input => input.classList.remove('border-red-500'));
    }
};

// Chart utilities (if using charts)
const SnapDxCharts = {
    // Create simple bar chart
    createBarChart: function(canvasId, data, options = {}) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const defaultOptions = {
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderColor: 'rgba(59, 130, 246, 1)',
            borderWidth: 2
        };
        
        const chartOptions = { ...defaultOptions, ...options };
        
        // Simple bar chart implementation
        const maxValue = Math.max(...data.values);
        const barWidth = canvas.width / data.values.length;
        
        data.values.forEach((value, index) => {
            const barHeight = (value / maxValue) * canvas.height;
            const x = index * barWidth;
            const y = canvas.height - barHeight;
            
            ctx.fillStyle = chartOptions.backgroundColor;
            ctx.fillRect(x, y, barWidth - 2, barHeight);
            
            ctx.strokeStyle = chartOptions.borderColor;
            ctx.lineWidth = chartOptions.borderWidth;
            ctx.strokeRect(x, y, barWidth - 2, barHeight);
        });
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    SnapDxUtils.log('SnapDx application initialized', 'info');
    
    // Check authentication status
    if (SnapDxAuth.isAuthenticated()) {
        SnapDxUtils.log('User is authenticated', 'info');
    } else {
        SnapDxUtils.log('User is not authenticated', 'info');
    }
    
    // Add global event listeners
    document.addEventListener('click', function(e) {
        // Handle modal close on backdrop click
        if (e.target.classList.contains('modal-overlay')) {
            const modal = e.target.closest('.modal-overlay');
            if (modal) {
                modal.classList.add('hidden');
            }
        }
        
        // Handle copy to clipboard
        if (e.target.hasAttribute('data-copy')) {
            const text = e.target.getAttribute('data-copy');
            SnapDxUI.copyToClipboard(text);
        }
    });
    
    // Handle form submissions
    document.addEventListener('submit', function(e) {
        if (e.target.hasAttribute('data-validate')) {
            if (!SnapDxForms.validateForm(e.target)) {
                e.preventDefault();
            }
        }
    });
    
    // Handle input validation
    document.addEventListener('blur', function(e) {
        if (e.target.hasAttribute('data-validate')) {
            if (!e.target.value.trim()) {
                SnapDxForms.showFieldError(e.target, 'This field is required');
            } else {
                SnapDxForms.clearFieldError(e.target);
            }
        }
    }, true);
});

// Export utilities for use in other scripts
window.SnapDx = {
    Utils: SnapDxUtils,
    API: SnapDxAPI,
    Auth: SnapDxAuth,
    UI: SnapDxUI,
    Forms: SnapDxForms,
    Charts: SnapDxCharts,
    Config: SnapDxConfig
}; 