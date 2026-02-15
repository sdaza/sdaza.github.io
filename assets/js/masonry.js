document.addEventListener("DOMContentLoaded", function () {
  var gridEl = document.querySelector(".grid");
  if (!gridEl) return;
  var msnry = new Masonry(gridEl, {
    gutter: 10,
    horizontalOrder: true,
    itemSelector: ".grid-item",
  });
  imagesLoaded(gridEl, function () {
    msnry.layout();
  });
});
