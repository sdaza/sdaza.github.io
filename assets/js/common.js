document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("a.abstract").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      var entry = el.closest(".pub-content") || el.parentElement.parentElement;
      var abs = entry.querySelector(".abstract.hidden");
      var bib = entry.querySelector(".bibtex.hidden");
      if (abs) abs.classList.toggle("open");
      if (bib) bib.classList.remove("open");
    });
  });
  document.querySelectorAll("a.bibtex").forEach(function (el) {
    el.addEventListener("click", function (e) {
      e.preventDefault();
      var entry = el.closest(".pub-content") || el.parentElement.parentElement;
      var bib = entry.querySelector(".bibtex.hidden");
      var abs = entry.querySelector(".abstract.hidden");
      if (bib) bib.classList.toggle("open");
      if (abs) abs.classList.remove("open");
    });
  });
});
