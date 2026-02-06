document.getElementById("registerForm").addEventListener("submit", async function (e) {
    e.preventDefault(); // stop normal submit

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ name, email, password })
        });

        const data = await response.json();

        if (data.success) {
            alert("Registration successful. Please login.");
            window.location.href = "/";
        } else {
            alert(data.message);
        }

    } catch (error) {
        alert("Server error. Please try again.");
        console.error(error);
    }
});
