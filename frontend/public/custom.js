// Set custom favicon
(function () {
  const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
  link.type = 'image/jpg';
  link.rel = 'icon';
  link.href = '/public/bedtimenews.jpg';
  document.getElementsByTagName('head')[0].appendChild(link);
})();

// Set custom page title
document.addEventListener('DOMContentLoaded', function() {
  document.title = '睡前消息知识库';
});
