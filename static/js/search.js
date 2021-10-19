window.onload = () => {
    let search = document.querySelector(".search");

    search.addEventListener("focus", () => {
        if(window.location.pathname != "/quote")
            window.location.pathname = "/quote";
    });

    search.addEventListener("search", (e) => {
        window.location.pathname = `/quote/${search.value}`;
    })

}

