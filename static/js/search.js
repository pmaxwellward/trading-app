window.onload = () => {
    let search = document.querySelector(".search");

    // Naviage to quote route if search bar is selected
    search.addEventListener("focus", () => {
        if(window.location.pathname != "/quote")
            window.location.pathname = "/quote";
    });

    // look up symbol name in search bar if user hits enter
    search.addEventListener("search", (e) => {
        window.location.pathname = `/quote/${search.value}`;
    })

}

