// Khởi tạo các phần tử giao diện cần tương tác
const themeToggle = document.querySelector("#theme-toggle");
const typingText = document.querySelector("#typing-text");
const shareButton = document.querySelector("#share-button");
const toast = document.querySelector("#toast");
const yearElement = document.querySelector("#current-year");

// Đọc theme đã lưu; nếu chưa có thì ưu tiên giao diện theo thiết bị
const getSavedTheme = () => {
  try {
    return localStorage.getItem("bio-link-theme");
  } catch {
    return null;
  }
};

const savedTheme = getSavedTheme();
const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
const initialTheme = savedTheme || (prefersLight ? "light" : "dark");

// Cập nhật giao diện, biểu tượng và nhãn hỗ trợ trình đọc màn hình
const setTheme = (theme) => {
  document.documentElement.dataset.theme = theme;

  const isDark = theme === "dark";
  themeToggle.innerHTML = isDark
    ? '<i class="fa-solid fa-sun" aria-hidden="true"></i>'
    : '<i class="fa-solid fa-moon" aria-hidden="true"></i>';

  themeToggle.setAttribute(
    "aria-label",
    isDark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"
  );

  try {
    localStorage.setItem("bio-link-theme", theme);
  } catch {
    // Bỏ qua nếu trình duyệt không cho phép lưu LocalStorage
  }
};

setTheme(initialTheme);

// Bật/tắt sáng tối khi nhấn nút
themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.dataset.theme;
  setTheme(currentTheme === "dark" ? "light" : "dark");
});

// Gõ nội dung bio lần lượt; hiển thị ngay nếu người dùng giảm chuyển động
const fullBio = typingText.textContent.trim();
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

if (reduceMotion) {
  typingText.textContent = fullBio;
} else {
  typingText.textContent = "";

  let characterIndex = 0;
  const typeNextCharacter = () => {
    if (characterIndex >= fullBio.length) return;

    typingText.textContent += fullBio[characterIndex];
    characterIndex += 1;
    window.setTimeout(typeNextCharacter, 38);
  };

  window.setTimeout(typeNextCharacter, 350);
}

// Sao chép URL trang; dùng textarea làm phương án dự phòng cho trình duyệt cũ
const copyPageUrl = async () => {
  const pageUrl = window.location.href;

  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(pageUrl);
    return;
  }

  const temporaryInput = document.createElement("textarea");
  temporaryInput.value = pageUrl;
  temporaryInput.setAttribute("readonly", "");
  temporaryInput.style.position = "fixed";
  temporaryInput.style.opacity = "0";
  document.body.appendChild(temporaryInput);
  temporaryInput.select();

  const copied = document.execCommand("copy");
  temporaryInput.remove();

  if (!copied) {
    throw new Error("Không thể sao chép liên kết.");
  }
};

// Hiển thị thông báo ngắn sau khi sao chép hoặc khi có lỗi
let toastTimer;

const showToast = (message) => {
  toast.textContent = message;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.textContent = "";
  }, 2600);
};

shareButton.addEventListener("click", async () => {
  try {
    await copyPageUrl();
    showToast("Đã sao chép liên kết Bio!");
  } catch {
    showToast("Không thể sao chép. Vui lòng thử lại.");
  }
});

// Tự động cập nhật năm ở chân trang
yearElement.textContent = new Date().getFullYear();
