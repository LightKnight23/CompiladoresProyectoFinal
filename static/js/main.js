// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Materialize components
    M.AutoInit();

    // DOM Elements
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const authSection = document.getElementById('auth-section');
    const adminSection = document.getElementById('admin-section');
    const logoutBtn = document.getElementById('logout-btn');
    const employeesTableBody = document.getElementById('employees-table-body');
    const pagination = document.getElementById('pagination');

    // Search form elements
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const searchType = document.getElementById('search-type');

    // Add event listener for search
    searchForm.addEventListener('submit', handleSearch);

    // Debounce function for search
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Handle search function
    async function handleSearch(e) {
    if (e) {
        e.preventDefault();
    }

    const searchTerm = searchInput.value.trim();
    const searchBy = searchType.value;

    if (!searchTerm) {
        return;  // Don't show error for empty search
    }

    try {
        const response = await fetch(
            `/api/employees/search?q=${encodeURIComponent(searchTerm)}&by=${searchBy}&page=1`,
            {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            }
        );

        if (response.status === 401) {
            handleLogout();
            return;
        }

        const data = await response.json();

        if (response.ok) {
            if (data.employees.length === 0) {
                employeesTableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="center-align">No employees found</td>
                    </tr>
                `;
                renderPagination(0, 1);
                showToast('No employees found', 'info');
            } else {
                renderEmployees(data.employees);
                renderPagination(data.total_pages, 1);
                showToast(`Found ${data.total} results`, 'success');
            }
        } else {
            showToast(data.error, 'error');
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed. Please try again.', 'error');
    }
}

    // Add debounced search for real-time results
    const debouncedSearch = debounce(handleSearch, 300);
    searchInput.addEventListener('input', debouncedSearch);

    let currentPage = 1;
    const itemsPerPage = 10;

    // Check authentication status on load
    checkAuthStatus();

    // Event Listeners
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    logoutBtn.addEventListener('click', handleLogout);

    // Authentication Functions
    function checkAuthStatus() {
        const token = localStorage.getItem('token');
        if (token) {
            showAdminSection();
            loadEmployees(1);
        } else {
            showAuthSection();
        }
    }

    function showAuthSection() {
        authSection.classList.remove('hidden');
        adminSection.classList.add('hidden');
    }

    function showAdminSection() {
        authSection.classList.add('hidden');
        adminSection.classList.remove('hidden');
    }

    async function handleLogin(e) {
        e.preventDefault();

        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('token', data.access_token);
                showToast('Login successful!', 'success');
                showAdminSection();
                loadEmployees(1);
            } else {
                showToast(data.error, 'error');
            }
        } catch (error) {
            showToast('Login failed. Please try again.', 'error');
        }
    }

    async function handleRegister(e) {
        e.preventDefault();

        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Registration successful! Please login.', 'success');
                const tabs = M.Tabs.getInstance(document.querySelector('.tabs'));
                tabs.select('login');
                registerForm.reset();
            } else {
                showToast(data.error, 'error');
            }
        } catch (error) {
            showToast('Registration failed. Please try again.', 'error');
        }
    }

    function handleLogout() {
        localStorage.removeItem('token');
        showAuthSection();
        showToast('Logged out successfully', 'success');
    }

    // Employee Management Functions
    async function loadEmployees(page) {
        try {
            const response = await fetch(`/api/employees?page=${page}&limit=${itemsPerPage}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.status === 401) {
                handleLogout();
                return;
            }

            const data = await response.json();

            if (response.ok) {
                renderEmployees(data.employees);
                renderPagination(data.total_pages, page);
                currentPage = page;
            } else {
                showToast('Failed to load employees', 'error');
            }
        } catch (error) {
            showToast('Error loading employees', 'error');
        }
    }

    function renderEmployees(employees) {
    employeesTableBody.innerHTML = employees.map(emp => `
        <tr>
            <td>${emp.emp_no}</td>
            <td>${emp.first_name} ${emp.last_name}</td>
            <td>${emp.title || 'N/A'}</td>
            <td>${emp.salary ? `$${emp.salary.toLocaleString()}` : 'N/A'}</td>
            <td>${emp.department || 'N/A'}</td>
            <td>
                <button class="btn-small waves-effect waves-light" onclick="editEmployee(${emp.emp_no})">
                    <i class="material-icons">edit</i>
                </button>
                <button class="btn-small red waves-effect waves-light" onclick="deleteEmployee(${emp.emp_no})">
                    <i class="material-icons">delete</i>
                </button>
            </td>
        </tr>
    `).join('');
}

    function renderPagination(totalPages, currentPage) {
        let paginationHTML = '';

        // Previous button
        paginationHTML += `
            <li class="${currentPage === 1 ? 'disabled' : 'waves-effect'}">
                <a href="#!" onclick="loadEmployees(${currentPage - 1})">
                    <i class="material-icons">chevron_left</i>
                </a>
            </li>
        `;

        // Page numbers
        for (let i = 1; i <= Math.min(10, totalPages); i++) {
        paginationHTML += `
            <li class="${i === currentPage ? 'active' : 'waves-effect'}">
                <a href="#!" onclick="loadEmployees(${i})">${i}</a>
            </li>
        `;
    }

        // Next button
        paginationHTML += `
            <li class="${currentPage === totalPages ? 'disabled' : 'waves-effect'}">
                <a href="#!" onclick="loadEmployees(${currentPage + 1})">
                    <i class="material-icons">chevron_right</i>
                </a>
            </li>
        `;

        pagination.innerHTML = paginationHTML;
    }

    // Edit Employee
    window.editEmployee = async function(empNo) {
        try {
            const response = await fetch(`/api/employees/${empNo}`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });

            if (response.ok) {
                const employee = await response.json();
                openEditModal(employee);
            } else {
                showToast('Failed to fetch employee details', 'error');
            }
        } catch (error) {
            showToast('Error fetching employee details', 'error');
        }
    }

    // Delete Employee
    window.deleteEmployee = async function(empNo) {
        if (confirm('Are you sure you want to delete this employee?')) {
            try {
                const response = await fetch(`/api/employees/${empNo}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (response.ok) {
                    showToast('Employee deleted successfully', 'success');
                    loadEmployees(currentPage);
                } else {
                    showToast('Failed to delete employee', 'error');
                }
            } catch (error) {
                showToast('Error deleting employee', 'error');
            }
        }
    }

    // Toast Messages
    function showToast(message, type) {
        M.toast({
            html: message,
            classes: `toast-${type}`,
            displayLength: 3000
        });
    }

    // Edit Modal Functions
    function openEditModal(employee) {
        const modal = document.getElementById('edit-modal');
        const modalInstance = M.Modal.getInstance(modal);

        // Fill form with employee data
        document.getElementById('edit-first-name').value = employee.first_name;
        document.getElementById('edit-last-name').value = employee.last_name;
        document.getElementById('edit-salary').value = employee.salary || '';

        // Update labels to be active
        M.updateTextFields();

        // Set employee number in data attribute
        modal.setAttribute('data-emp-no', employee.emp_no);

        modalInstance.open();
    }

    // Handle Edit Form Submit
    document.getElementById('edit-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const empNo = document.getElementById('edit-modal').getAttribute('data-emp-no');
        const formData = {
            first_name: document.getElementById('edit-first-name').value,
            last_name: document.getElementById('edit-last-name').value,
            salary: parseInt(document.getElementById('edit-salary').value) || null
        };

        try {
            const response = await fetch(`/api/employees/${empNo}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                M.Modal.getInstance(document.getElementById('edit-modal')).close();
                showToast('Employee updated successfully', 'success');
                loadEmployees(currentPage);
            } else {
                showToast('Failed to update employee', 'error');
            }
        } catch (error) {
            showToast('Error updating employee', 'error');
        }
    });

    // Make loadEmployees available globally
    window.loadEmployees = loadEmployees;
});