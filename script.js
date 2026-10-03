// Lấy các phần tử giao diện cần tương tác
const themeToggle = document.querySelector("#theme-toggle");
const typingText = document.querySelector("#typing-text");
const shareButton = document.querySelector("#share-button");
const toast = document.querySelector("#toast");
const yearElement = document.querySelector("#current-year");

// Đọc giao diện đã lưu trong trình duyệt
const getSavedTheme = () => {
  try {
    return localStorage.getItem("bio-link-theme");
  } catch {
    return null;
  }
};

// Chọn giao diện đã lưu hoặc theo thiết lập của thiết bị
const savedTheme = getSavedTheme();
const prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
const initialTheme = savedTheme || (prefersLight ? "light" : "dark");

// Đổi giao diện, cập nhật biểu tượng và lưu lựa chọn
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
    // Bỏ qua nếu trình duyệt không cho phép sử dụng LocalStorage
  }
};

setTheme(initialTheme);

// Bật hoặc tắt giao diện sáng tối khi nhấn nút
themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.dataset.theme;
  setTheme(currentTheme === "dark" ? "light" : "dark");
});

// Tạo hiệu ứng gõ chữ cho phần tiểu sử
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

// Sao chép URL trang, có phương án dự phòng cho trình duyệt cũ
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

// Hiển thị thông báo sau khi sao chép hoặc khi có lỗi
let toastTimer;

const showToast = (message) => {
  toast.textContent = message;
  window.clearTimeout(toastTimer);

  toastTimer = window.setTimeout(() => {
    toast.textContent = "";
  }, 2600);
};

// Xử lý sự kiện chia sẻ trang
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

// Ánh sáng nền và hạt lấp lánh theo con trỏ chuột
const supportsFinePointer = window.matchMedia("(pointer: fine)").matches;
let lastSparkTime = 0;

if (supportsFinePointer && !reduceMotion) {
  document.addEventListener("pointermove", (event) => {
    // Cập nhật vị trí ánh sáng nền theo chuột
    document.documentElement.style.setProperty("--mouse-x", `${event.clientX}px`);
    document.documentElement.style.setProperty("--mouse-y", `${event.clientY}px`);

    // Giới hạn số hạt được tạo để hiệu ứng chạy mượt
    const now = performance.now();
    if (now - lastSparkTime < 55) return;
    lastSparkTime = now;

    // Tạo hạt sáng và cho nó tự xóa sau khi chạy hiệu ứng
    const spark = document.createElement("span");
    spark.className = "mouse-spark";
    spark.style.left = `${event.clientX}px`;
    spark.style.top = `${event.clientY}px`;
    spark.style.setProperty("--drift-x", `${(Math.random() - 0.5) * 34}px`);
    spark.style.setProperty("--drift-y", `${(Math.random() - 0.5) * 34}px`);

    document.body.appendChild(spark);
    spark.addEventListener("animationend", () => spark.remove(), { once: true });
  });
}
