const eventTitle = document.getElementById("event-title");
const eventTicker = window.location.pathname.split("/").pop();
const eventPlatform = document.getElementById("event-platform");
const eventStatus = document.getElementById("event-status");
const eventVolume = document.getElementById("event-volume");
const eventUpdated = document.getElementById("event-updated");
const contractClose = document.getElementById("contract-close");
const contractButtons = document.getElementById("contract-buttons");
const contractSwitcher = document.querySelector(".contract-switcher");
const yesPrice = document.getElementById("yes-price");
const noPrice = document.getElementById("no-price");
const yesBar = document.getElementById("yes-bar");
const noBar = document.getElementById("no-bar");

function formatVolume(volume) {
    if (volume >= 1000000) {
        return "$" + (volume / 1000000).toFixed(1) + "M";
    }

    if (volume >= 1000) {
        return "$" + (volume / 1000).toFixed(0) + "K";
    }

    return "$" + volume.toFixed(0);
}

function formatDate(date) {
    return new Date(date).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
}

function selectContract(contract, selectedButton) {
    const yes = Math.round(contract.yes_price * 100);
    const no = 100 - yes;

    yesPrice.textContent = yes + "%";
    noPrice.textContent = no + "%";
    yesBar.style.width = yes + "%";
    noBar.style.width = no + "%";
    eventStatus.textContent = contract.status;
    eventVolume.textContent = formatVolume(contract.volume);
    contractClose.textContent = formatDate(contract.close_time);
    eventUpdated.textContent = formatDate(contract.observed_at);

    for (const button of contractButtons.children) {
        button.classList.remove("contract-button--selected");
    }

    selectedButton.classList.add("contract-button--selected");
}

function showContracts(contracts) {
    for (let i = 0; i < contracts.length; i++) {
        const contract = contracts[i];
        const button = document.createElement("button");
        const name = contract.outcome_label || contract.title;
        const price = Math.round(contract.yes_price * 100);

        button.className = "contract-button";
        button.textContent = name + " · " + price + "%";
        button.addEventListener("click", function () {
            selectContract(contract, button);
        });
        contractButtons.appendChild(button);
    }

    selectContract(contracts[0], contractButtons.children[0]);
}

function showStickyBorder() {
    if (window.scrollY >= contractSwitcher.offsetTop) {
        contractSwitcher.classList.add("contract-switcher--stuck");
    } else {
        contractSwitcher.classList.remove("contract-switcher--stuck");
    }
}

window.addEventListener("scroll", showStickyBorder);
showStickyBorder();

fetch("/api/events/" + eventTicker)
    .then(function (response) {
        return response.json();
    })
    .then(function (event) {
        eventTitle.textContent = event.display_name;
        document.title = event.display_name;
        eventPlatform.textContent = event.platform;
        showContracts(event.contracts);
    })
    .catch(function () {
        eventTitle.textContent = "Unable to load event";
        eventPlatform.textContent = "Unavailable";
        eventStatus.textContent = "Unavailable";
        eventVolume.textContent = "Unavailable";
        contractClose.textContent = "Unavailable";
        eventUpdated.textContent = "Unavailable";
    });
