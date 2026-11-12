const input = document.querySelector("[data-profile-photo-input]");
const preview = document.querySelector("[data-profile-photo-preview]");
const filename = document.querySelector("[data-profile-photo-filename]");

if (input && preview && filename) {
  input.addEventListener("change", () => {
    const [file] = input.files;
    if (!file) return;

    const image = document.createElement("img");
    image.src = URL.createObjectURL(file);
    image.alt = `Preview of ${file.name}`;
    image.addEventListener("load", () => URL.revokeObjectURL(image.src), { once: true });
    preview.replaceChildren(image);
    filename.textContent = file.name;
  });
}
