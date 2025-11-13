// /ui/static/ui/editor.js
document.addEventListener("DOMContentLoaded", function () {
  //console.log("✅ Quill 安全版起動");

  if (typeof Quill === "undefined") {
    //console.warn("❌ Quillが見つかりません。終了。");
    return;
  }

  // 複数の textarea に対応
  const textareas = document.querySelectorAll("textarea.richtext, #id_body");
  if (!textareas.length) {
    //console.warn("⚠️ 対象textareaなし");
    return;
  }

  textareas.forEach((textarea) => {
    // 二重初期化防止
    if (textarea.dataset.editorInitialized) return;
    textarea.dataset.editorInitialized = true;

    // Quillエディタ用のdivを作成
    const wrapper = document.createElement("div");
    wrapper.classList.add("quill-editor");
    textarea.style.display = "none";
    textarea.parentNode.insertBefore(wrapper, textarea);

    // Quill本体を初期化
    const quill = new Quill(wrapper, { theme: "snow" });
    quill.root.innerHTML = textarea.value || "";

    // 送信時にtextareaへ反映
    const form = textarea.closest("form");
    if (form) {
      form.addEventListener("submit", () => {
        textarea.value = quill.root.innerHTML;
        //console.log("💾 textareaに内容を反映:", textarea.value.slice(0, 50));
      });
    }

    function initQuillForModal(modalSelector) {
      const modal = document.querySelector(modalSelector);
      if (!modal) return;

      const textarea = modal.querySelector("textarea.richtext");
      if (!textarea) return;

      if (textarea.dataset.editorInitialized) return;
      textarea.dataset.editorInitialized = true;

      const wrapper = document.createElement("div");
      wrapper.classList.add("quill-editor");
      textarea.style.display = "none";
      textarea.parentNode.insertBefore(wrapper, textarea);

      const quill = new Quill(wrapper, { theme: "snow" });
      quill.root.innerHTML = textarea.value || "";

      // ✅ 保存ボタン押した時に textarea に戻す
      const form = textarea.closest("form");
      if (form) {
        form.addEventListener("submit", () => {
          textarea.value = quill.root.innerHTML;
          //console.log("💾 Quill内容を反映:", textarea.value.slice(0, 50));
        });
      }

      //console.log("🪄 Quill初期化完了:", modalSelector);
    }

    // ✅ モーダル開くときに Quill を準備する
    document.addEventListener("click", function (e) {
      if (e.target.matches(".open-temp-btn, #addTempBtn")) {
        setTimeout(() => {
          initQuillForModal("#templateModal");
        }, 200);
      }
    });
    //console.log("✅ Quill初期化完了:", textarea.id || "(no id)");
  });
});
