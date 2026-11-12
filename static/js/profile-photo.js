const input = document.querySelector("[data-profile-photo-input]");
const preview = document.querySelector("[data-profile-photo-preview]");
const filename = document.querySelector("[data-profile-photo-filename]");
const trigger = document.querySelector("[data-profile-photo-trigger]");
const dialog = document.querySelector("[data-photo-cropper]");
const canvas = document.querySelector("[data-crop-canvas]");
const stage = document.querySelector("[data-crop-stage]");
const zoomControl = document.querySelector("[data-crop-zoom]");
const applyButton = document.querySelector("[data-crop-apply]");
const cropError = document.querySelector("[data-crop-error]");

if (input && preview && filename && trigger && dialog && canvas && stage && zoomControl && applyButton && cropError) {
  const context = canvas.getContext("2d");
  const cropSize = canvas.width;
  let image = null;
  let sourceFile = null;
  let baseScale = 1;
  let zoom = 1;
  let offsetX = 0;
  let offsetY = 0;
  let activePointer = null;
  let lastX = 0;
  let lastY = 0;

  const imageSize = () => ({
    width: image.naturalWidth * baseScale * zoom,
    height: image.naturalHeight * baseScale * zoom,
  });

  const clampPosition = () => {
    const size = imageSize();
    offsetX = Math.min(0, Math.max(cropSize - size.width, offsetX));
    offsetY = Math.min(0, Math.max(cropSize - size.height, offsetY));
  };

  const draw = () => {
    if (!image) return;
    clampPosition();
    const size = imageSize();
    context.clearRect(0, 0, cropSize, cropSize);
    context.drawImage(image, offsetX, offsetY, size.width, size.height);
  };

  const showError = (message) => {
    cropError.textContent = message;
    cropError.hidden = false;
  };

  const openEditor = (file) => {
    cropError.hidden = true;
    const objectUrl = URL.createObjectURL(file);
    const candidate = new Image();
    candidate.addEventListener("load", () => {
      URL.revokeObjectURL(objectUrl);
      image = candidate;
      sourceFile = file;
      zoom = 1;
      zoomControl.value = "1";
      baseScale = Math.max(cropSize / image.naturalWidth, cropSize / image.naturalHeight);
      const size = imageSize();
      offsetX = (cropSize - size.width) / 2;
      offsetY = (cropSize - size.height) / 2;
      draw();
      dialog.showModal();
    }, { once: true });
    candidate.addEventListener("error", () => {
      URL.revokeObjectURL(objectUrl);
      input.value = "";
      showError("We could not open that image. Choose a JPEG, PNG, or WebP file.");
      dialog.showModal();
    }, { once: true });
    candidate.src = objectUrl;
  };

  trigger.addEventListener("click", () => input.click());

  input.addEventListener("change", () => {
    const [file] = input.files;
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      input.value = "";
      showError("Choose a JPEG, PNG, or WebP image.");
      dialog.showModal();
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      input.value = "";
      showError("Choose an image smaller than 5 MB.");
      dialog.showModal();
      return;
    }
    openEditor(file);
  });

  zoomControl.addEventListener("input", () => {
    if (!image) return;
    const previousScale = baseScale * zoom;
    const centerX = (cropSize / 2 - offsetX) / previousScale;
    const centerY = (cropSize / 2 - offsetY) / previousScale;
    zoom = Number(zoomControl.value);
    const nextScale = baseScale * zoom;
    offsetX = cropSize / 2 - centerX * nextScale;
    offsetY = cropSize / 2 - centerY * nextScale;
    draw();
  });

  stage.addEventListener("pointerdown", (event) => {
    if (!image) return;
    activePointer = event.pointerId;
    lastX = event.clientX;
    lastY = event.clientY;
    stage.setPointerCapture(activePointer);
    stage.classList.add("is-dragging");
  });

  stage.addEventListener("pointermove", (event) => {
    if (event.pointerId !== activePointer) return;
    const ratio = cropSize / canvas.getBoundingClientRect().width;
    offsetX += (event.clientX - lastX) * ratio;
    offsetY += (event.clientY - lastY) * ratio;
    lastX = event.clientX;
    lastY = event.clientY;
    draw();
  });

  const finishDrag = (event) => {
    if (event.pointerId !== activePointer) return;
    activePointer = null;
    stage.classList.remove("is-dragging");
  };

  stage.addEventListener("pointerup", finishDrag);
  stage.addEventListener("pointercancel", finishDrag);

  applyButton.addEventListener("click", () => {
    if (!image || !sourceFile) return;
    applyButton.disabled = true;
    applyButton.textContent = "Preparing photo…";
    canvas.toBlob((blob) => {
      if (!blob) {
        showError("We could not prepare that crop. Try another image.");
        applyButton.disabled = false;
        applyButton.textContent = "Use this photo";
        return;
      }
      const croppedFile = new File([blob], "profile.webp", { type: "image/webp" });
      const transfer = new DataTransfer();
      transfer.items.add(croppedFile);
      input.files = transfer.files;

      const previewImage = document.createElement("img");
      previewImage.src = URL.createObjectURL(blob);
      previewImage.width = 112;
      previewImage.height = 112;
      previewImage.alt = `Preview of cropped ${sourceFile.name}`;
      previewImage.style.cssText = "display:block;width:112px;height:112px;max-width:112px;object-fit:cover;";
      previewImage.addEventListener("load", () => URL.revokeObjectURL(previewImage.src), { once: true });
      preview.replaceChildren(previewImage);
      filename.textContent = `${sourceFile.name} · crop ready`;
      dialog.returnValue = "apply";
      dialog.close();
      applyButton.disabled = false;
      applyButton.textContent = "Use this photo";
    }, "image/webp", 0.86);
  });

  dialog.addEventListener("close", () => {
    if (dialog.returnValue !== "apply") input.value = "";
    image = null;
    sourceFile = null;
    dialog.returnValue = "";
  });
}
