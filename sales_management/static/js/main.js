document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach((toastEl) => {
        const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
        toast.show();
    });

    document.querySelectorAll("[data-loading-form]").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector("button[type='submit']");
            if (!button || button.disabled) {
                return;
            }
            const spinner = button.querySelector(".spinner-border");
            button.classList.add("is-loading");
            button.disabled = true;
            if (spinner) {
                spinner.classList.remove("d-none");
            }
        });
    });
});
