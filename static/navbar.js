(function () {
  var toggle = document.getElementById('navbarToggle');
  var links = document.getElementById('navbarLinks');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }
})();
