
// Load navigation bar from external file
fetch('/nav.html')
  .then(response => response.text())
  .then(data => {
    const placeholder = document.getElementById('nav-placeholder');
    if (placeholder) {
      placeholder.innerHTML = data;
    }
  })
  .catch(err => console.error('Error loading navigation:', err));