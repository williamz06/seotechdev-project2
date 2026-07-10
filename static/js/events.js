const eventsElement = document.getElementById("events");
const barColors = ["#2563eb", "#16a34a", "#9333ea"];

function formatVolume(volume) {
    if (volume >= 1000000) {
        return "$" + (volume / 1000000).toFixed(1) + "M";
    }

    if (volume >= 1000) {
        return "$" + (volume / 1000).toFixed(0) + "K";
    }

    return "$" + volume.toFixed(0);
}

function showEvents(events) {
    eventsElement.innerHTML = "";

    for (const event of events) {
        const card = document.createElement("article");
        const statusClass = event.status === "open" || event.status === "active" ? "badge--positive" : "badge--negative";
        card.className = "event-card card";

        let contractList = "";
        const contracts = event.contracts.slice(0, 3);
        for (let i = 0; i < contracts.length; i++) {
            const contract = contracts[i];
            const name = contract.outcome_label || contract.title;
            const price = Math.round(contract.yes_price * 100);
            contractList += "<div class='contract-item'>" +
                "<div class='contract-row'><span>" + name + "</span><strong>" + price + "%</strong></div>" +
                "<div class='contract-bar'><div class='contract-bar__fill' style='width: " + price + "%; background: " + barColors[i] + "'></div></div>" +
                "</div>";
        }

        if (event.contract_count > 3) {
            contractList += "<p class='more-contracts'>+ " + (event.contract_count - 3) + " more contracts</p>";
        }

        card.innerHTML = "<div class='event-card__top-row'>" +
            "<p class='event-card__metadata'>" + event.platform + " · " + event.contract_count + " contracts</p>" +
            "<p class='badge " + statusClass + "'>" + event.status + "</p>" +
            "</div>" +
            "<h2 class='event-card__title'>" + event.display_name + "</h2>" +
            "<div class='contract-list'>" + contractList + "</div>" +
            "<div class='event-card__footer'>" +
            "<p>Volume: " + formatVolume(event.volume) + "</p>" +
            "<a href='/event/" + event.event_ticker + "'>View contracts →</a>" +
            "</div>";

        eventsElement.appendChild(card);
    }
}

fetch("/api/events")
    .then(function (response) {
        return response.json();
    })
    .then(function (data) {
        showEvents(data.events);
    })
    .catch(function () {
        eventsElement.innerHTML = "<p>Unable to load market events.</p>";
    });
