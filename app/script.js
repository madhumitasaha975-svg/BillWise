// ==========================================
// HELPER: DECODE JWT TOKEN & ROUTE USER
// ==========================================
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch(e) {
        return null;
    }
}

// 🚨 IMPORTANT: Change this to YOUR exact admin email address!
const ADMIN_EMAIL = "harshdeep@admin.com"; 

function routeUser(token) {
    const payload = parseJwt(token);
    if (payload && payload.sub === ADMIN_EMAIL) {
        window.location.href = "dashboardadmin.html"; // Route to Admin
    } else {
        window.location.href = "dashboardcustomer.html"; // Route to Customer
    }
}

// ==========================================
// UI TOGGLE LOGIC
// ==========================================
function toggleForms() {
    const signinForm = document.getElementById('signin-form');
    const signupForm = document.getElementById('signup-form');
    const formTitle = document.getElementById('form-title');
    const formSubtitle = document.getElementById('form-subtitle');
    const toggleContainer = document.getElementById('toggle-container');

    if (signinForm.classList.contains('hidden')) {
        // Switch to Sign In
        signinForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        formTitle.innerText = 'Sign In';
        formSubtitle.innerText = 'Welcome back to the Billing Platform';
        toggleContainer.innerHTML = 'Don\'t have an account? <a href="#" onclick="toggleForms(); return false;">Sign up</a>';
    } else {
        // Switch to Sign Up
        signinForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        formTitle.innerText = 'Create Account';
        formSubtitle.innerText = 'Get started with BillWise'; 
        toggleContainer.innerHTML = 'Already have an account? <a href="#" onclick="toggleForms(); return false;">Sign in</a>';
    }
}

// ==========================================
// REGISTRATION LOGIC (Sign Up)
// ==========================================
document.getElementById('signup-form').addEventListener('submit', async (e) => {
    e.preventDefault(); 

    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;

    try {
        const response = await fetch('http://127.0.0.1:8000/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email: email, password: password })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Account created successfully! Please sign in.');
            toggleForms(); // Automatically switch back to login view
            
            // Auto-fill the email in the sign-in form for convenience
            document.getElementById('signin-email').value = email; 
        } else {
            alert('Registration Failed: ' + data.detail);
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('Could not connect to the server.');
    }
});

// ==========================================
// LOGIN LOGIC (Sign In)
// ==========================================
document.getElementById('signin-form').addEventListener('submit', async (e) => {
    e.preventDefault(); 

    const email = document.getElementById('signin-email').value;
    const password = document.getElementById('signin-password').value;

    const formData = new URLSearchParams();
    formData.append('username', email); 
    formData.append('password', password);

    try {
        const response = await fetch('http://127.0.0.1:8000/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Save the token securely in the browser
            localStorage.setItem('access_token', data.access_token);
            
            // 🚀 SMART REDIRECT
            routeUser(data.access_token);
        } else {
            alert('Sign In Failed: ' + data.detail);
        }
    } catch (error) {
        console.error('Login error:', error);
        alert('Could not connect to the server.');
    }
});

// ==========================================
// GOOGLE AUTH LOGIC
// ==========================================
async function handleGoogleLogin(response) {
    // Google hands us a secure JWT credential
    const googleToken = response.credential;

    try {
        const res = await fetch('http://127.0.0.1:8000/auth/google', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ token: googleToken })
        });

        const data = await res.json();

        if (res.ok) {
            // Save YOUR backend's token to the browser
            localStorage.setItem('access_token', data.access_token);
            console.log("Token saved:", data.access_token);
            
            // 🚀 SMART REDIRECT
            routeUser(data.access_token);
        } else {
            alert('Google Sign In Failed: ' + data.detail);
        }
    } catch (error) {
        console.error('Google auth error:', error);
        alert('Could not connect to the server.');
    }
}