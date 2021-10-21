// caret positions for each link
const LINK_POS = {
    "/": "11%",
    "quote": "34.5%",
    "deposit": "60%",
    "history": "85%",
    "login" : "75%",
    "register": "24%"
}  


// Place caret on link for current route
document.addEventListener("DOMContentLoaded", () => {
    
    let path = window.location.pathname;
    let link = document.getElementById(path);
    let caret = document.getElementById("caret");

    switch(path) {        
        case "/":
            caret.style.left = LINK_POS["/"];
            break;
        case "/quote":
            caret.style.left = LINK_POS["quote"];         
            break;
        case "/deposit":
            caret.style.left = LINK_POS["deposit"];
            break;
        case "/history":
            caret.style.left = LINK_POS["history"];
            break;
        case "/login":
            caret.style.left = LINK_POS["login"];
            break;
        case "/register":
            caret.style.left = LINK_POS["register"];
            break;
    }

    if (link) {
        
        link.style.fontWeight = "600";
        caret.classList.add("caret");

        if (path == "/login" || path == "/register") 
            caret.classList.add("caret-login");

    } else {
        caret.style.opacity = 0;
    }

});


// Caret animation
function transition(id, val) {
    
    let caret = document.querySelector(".caret");
    let currentLink = document.getElementById(window.location.pathname);
    let link = document.getElementById(id);
    
    if (currentLink) {
        currentLink.style.fontWeight = "300";
    
        link.style.fontWeight = "600";
        caret.style.left = val;
        
        caret.addEventListener("transitionend", (e) => {
            redirect(id);
        }, false);
    } else {
        redirect(id);
    }

}



let redirect = function (path) {
    console.log(path);
    window.location.pathname = path;
}