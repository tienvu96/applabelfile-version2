document.addEventListener('DOMContentLoaded', function() {
    // Optional: You can add smooth scrolling for section links if they exist
    const links = document.querySelectorAll('a[href^="#"]');

    links.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            const target = document.querySelector(this.getAttribute('href'));
            window.scrollTo({
                top: target.offsetTop,
                behavior: 'smooth'
            });
        });
    });

    // Optional: Add a fade-in effect when the sections come into view
    const sections = document.querySelectorAll('.section');

    window.addEventListener('scroll', function() {
        sections.forEach(section => {
            const sectionTop = section.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (sectionTop <= windowHeight - 100) {
                section.classList.add('fade-in');
            }
        });
    });
});
