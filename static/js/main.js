/* ============================================================
   SmileCraft Dental Clinic - Main JavaScript
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

    // ========== LOADING SCREEN ==========
    const loadingScreen = document.getElementById('loading-screen');
    if (loadingScreen) {
        setTimeout(() => {
            loadingScreen.style.opacity = '0';
            loadingScreen.style.transition = 'opacity 0.5s ease';
            setTimeout(() => {
                loadingScreen.style.display = 'none';
                document.body.style.overflow = 'auto';
            }, 500);
        }, 2200);
    }

    // ========== NAVBAR SCROLL EFFECT ==========
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', () => {
        if (navbar) {
            if (window.pageYOffset > 80) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    });

    // ========== SMOOTH SCROLLING ==========
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const navHeight = navbar ? navbar.offsetHeight : 0;
                const targetPosition = target.offsetTop - navHeight - 10;
                window.scrollTo({ top: targetPosition, behavior: 'smooth' });
            }
            const navMenu = document.getElementById('nav-menu');
            const navToggle = document.getElementById('nav-toggle');
            if (navMenu) navMenu.classList.remove('active');
            if (navToggle) navToggle.classList.remove('active');
        });
    });

    // ========== MOBILE MENU TOGGLE ==========
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            navMenu.classList.toggle('active');
        });
    }

    // ========== ACTIVE NAV LINK ON SCROLL ==========
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    function updateActiveLink() {
        const scrollY = window.pageYOffset;
        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 150;
            const sectionId = section.getAttribute('id');
            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                navLinks.forEach(link => {
                    link.classList.remove('active');
                    if (link.getAttribute('href') === '#' + sectionId) {
                        link.classList.add('active');
                    }
                });
            }
        });
    }
    window.addEventListener('scroll', updateActiveLink);

    // ========== SCROLL REVEAL ANIMATION ==========
    const revealElements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right');
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15, rootMargin: '0px 0px -50px 0px' });
    revealElements.forEach(el => revealObserver.observe(el));

    // ========== STATS COUNTER ANIMATION ==========
    const statNumbers = document.querySelectorAll('.stat-number');
    let statsAnimated = false;
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !statsAnimated) {
                statsAnimated = true;
                animateCounters();
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    const statsRow = document.querySelector('.stats-row');
    if (statsRow) statsObserver.observe(statsRow);

    function animateCounters() {
        statNumbers.forEach(counter => {
            const target = parseFloat(counter.getAttribute('data-target'));
            const isDecimal = counter.getAttribute('data-decimal') === 'true';
            const duration = 2000;
            const startTime = performance.now();
            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const current = target * easeProgress;
                if (isDecimal) {
                    counter.textContent = current.toFixed(1);
                } else {
                    counter.textContent = Math.floor(current).toLocaleString();
                }
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = isDecimal ? target.toFixed(1) : target.toLocaleString();
                }
            }
            requestAnimationFrame(updateCounter);
        });
    }

    // ========== TESTIMONIAL SLIDER ==========
    const track = document.getElementById('testimonials-track');
    const dots = document.querySelectorAll('#testimonial-dots .dot');
    let currentSlide = 0;
    let slideInterval;
    let totalSlides = 0;
    if (track) {
        const cards = track.querySelectorAll('.testimonial-card');
        totalSlides = cards.length;
        function goToSlide(index) {
            currentSlide = index;
            track.style.transform = 'translateX(' + (-index * 100) + '%)';
            dots.forEach((dot, i) => { dot.classList.toggle('active', i === index); });
        }
        function nextSlide() { goToSlide((currentSlide + 1) % totalSlides); }
        function startAutoRotate() { slideInterval = setInterval(nextSlide, 5000); }
        function stopAutoRotate() { clearInterval(slideInterval); }
        startAutoRotate();
        dots.forEach(dot => {
            dot.addEventListener('click', () => {
                goToSlide(parseInt(dot.getAttribute('data-index')));
                stopAutoRotate();
                startAutoRotate();
            });
        });
        const sliderContainer = document.querySelector('.testimonials-slider');
        if (sliderContainer) {
            sliderContainer.addEventListener('mouseenter', stopAutoRotate);
            sliderContainer.addEventListener('mouseleave', startAutoRotate);
        }
    }

    // ========== FAQ ACCORDION ==========
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        question.addEventListener('click', () => {
            const isOpen = item.classList.contains('active');
            faqItems.forEach(other => {
                other.classList.remove('active');
                const otherToggle = other.querySelector('.faq-toggle');
                if (otherToggle) otherToggle.textContent = '+';
            });
            if (!isOpen) {
                item.classList.add('active');
                const toggle = item.querySelector('.faq-toggle');
                if (toggle) toggle.textContent = '\u2212';
            }
        });
    });

    // ========== APPOINTMENT FORM ==========
    const appointmentForm = document.getElementById('appointment-form');
    if (appointmentForm) {
        const dateInput = document.getElementById('apt-date');
        if (dateInput) {
            const today = new Date().toISOString().split('T')[0];
            dateInput.setAttribute('min', today);
        }
        appointmentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('apt-submit-btn');
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoader = submitBtn.querySelector('.btn-loader');
            const formData = {
                name: document.getElementById('apt-name').value.trim(),
                phone: document.getElementById('apt-phone').value.trim(),
                email: document.getElementById('apt-email').value.trim(),
                preferred_date: document.getElementById('apt-date').value,
                preferred_time: document.getElementById('apt-time').value,
                service: document.getElementById('apt-service').value,
                message: document.getElementById('apt-message').value.trim()
            };
            if (!formData.name || formData.name.length < 2) { showToast('Please enter your full name (at least 2 characters).', 'error'); return; }
            const phoneClean = formData.phone.replace(/[\s\-\(\)\+]/g, '');
            if (!phoneClean || phoneClean.length < 7 || phoneClean.length > 15) { showToast('Please enter a valid phone number.', 'error'); return; }
            const emailPattern = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
            if (!emailPattern.test(formData.email)) { showToast('Please enter a valid email address.', 'error'); return; }
            if (!formData.preferred_date) { showToast('Please select a preferred date.', 'error'); return; }
            if (!formData.preferred_time) { showToast('Please select a preferred time.', 'error'); return; }
            if (!formData.service) { showToast('Please select a service.', 'error'); return; }
            btnText.style.display = 'none';
            btnLoader.style.display = 'flex';
            submitBtn.disabled = true;
            try {
                const response = await fetch('/api/appointments', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                if (data.success) {   
                showToast(data.message || 'Appointment booked successfully!', 'success');btnText.style.display = 'flex'; btnLoader.style.display = 'none'; submitBtn.disabled = false;
                } else {
                    showToast(data.message || 'Failed to book appointment. Please try again.', 'error');
                    btnText.style.display = 'flex'; btnLoader.style.display = 'none'; submitBtn.disabled = false;
                }
            } catch (err) {
                showToast('Connection error. Please check your internet and try again.', 'error');
                btnText.style.display = 'flex'; btnLoader.style.display = 'none'; submitBtn.disabled = false;
            }
        });
    }

    // ========== CONTACT FORM ==========
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('contact-submit-btn');
            const btnText = submitBtn.querySelector('.btn-text');
            const btnLoader = submitBtn.querySelector('.btn-loader');
            const formData = {
                name: document.getElementById('contact-name').value.trim(),
                email: document.getElementById('contact-email').value.trim(),
                phone: document.getElementById('contact-phone').value.trim(),
                message: document.getElementById('contact-message').value.trim()
            };
            if (!formData.name || formData.name.length < 2) { showToast('Please enter your full name.', 'error'); return; }
            const emailPattern = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
            if (!emailPattern.test(formData.email)) { showToast('Please enter a valid email address.', 'error'); return; }
            if (!formData.message || formData.message.length < 10) { showToast('Please enter a message (at least 10 characters).', 'error'); return; }
            btnText.style.display = 'none'; btnLoader.style.display = 'flex'; submitBtn.disabled = true;
            try {
                const response = await fetch('/api/contact', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                if (data.success) {
                    showToast(data.message || 'Message sent successfully!', 'success');
                    contactForm.reset();
                } else {
                    showToast(data.message || 'Failed to send message. Please try again.', 'error');
                }
            } catch (err) {
                showToast('Connection error. Please try again.', 'error');
            } finally {
                btnText.style.display = 'flex'; btnLoader.style.display = 'none'; submitBtn.disabled = false;
            }
        });
    }

    // ========== TOAST NOTIFICATIONS ==========
    window.showToast = function(message, type) {
        type = type || 'success';
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.innerHTML = '<div class="toast-icon">' + (type === 'success' ? '\u2705' : '\u274C') + '</div>' +
            '<div class="toast-message">' + message + '</div>' +
            '<button class="toast-close" onclick="this.parentElement.remove()">\u00D7</button>';
        container.appendChild(toast);
        requestAnimationFrame(() => { toast.classList.add('show'); });
        setTimeout(() => {
            toast.classList.add('hiding');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    };

    // ========== HERO PARALLAX EFFECT ==========
    const hero = document.querySelector('.hero');
    if (hero) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const heroHeight = hero.offsetHeight;
            if (scrolled < heroHeight) {
                const bgAnim = hero.querySelector('.hero-bg-animation');
                if (bgAnim) { bgAnim.style.transform = 'translateY(' + (scrolled * 0.3) + 'px)'; }
            }
        });
    }

    // ========== INPUT FOCUS ANIMATION ==========
    document.querySelectorAll('.form-group input, .form-group select, .form-group textarea').forEach(input => {
        input.addEventListener('focus', function() { this.closest('.form-group').classList.add('focused'); });
        input.addEventListener('blur', function() { this.closest('.form-group').classList.remove('focused'); });
    });

});
