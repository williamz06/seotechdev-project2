const kalshiLink = document.getElementById("kalshi-link");
const eventTitle = document.getElementById("event-title");
const eventTicker = window.location.pathname.split("/").pop();
const eventPlatform = document.getElementById("event-platform");
const eventStatus = document.getElementById("event-status");
const eventVolume = document.getElementById("event-volume");
const eventUpdated = document.getElementById("event-updated");
const contractClose = document.getElementById("contract-close");
const kalshiLink = document.getElementById("kalshi-link");
const contractButtons = document.getElementById("contract-buttons");
const contractSwitcher = document.querySelector(".contract-switcher");
const yesPrice = document.getElementById("yes-price");
const noPrice = document.getElementById("no-price");
const yesBar = document.getElementById("yes-bar");
const noBar = document.getElementById("no-bar");
const comparisonMarket = document.getElementById("comparison-market");
const comparisonSocial = document.getElementById("comparison-social");
const comparisonMarketBar = document.getElementById("comparison-market-bar");
const comparisonSocialBar = document.getElementById("comparison-social-bar");
const comparisonGap = document.getElementById("comparison-gap");
const comparisonExplanation = document.getElementById("comparison-explanation");
const discussionList = document.getElementById("discussion-list");
const coverageSource = document.getElementById("coverage-source");
const coveragePosts = document.getElementById("coverage-posts");
const coverageAuthors = document.getElementById("coverage-authors");
const coveragePredictions = document.getElementById("coverage-predictions");

let selectedContract;
let socialData;
let discussionPosts = [];
let discussionLoaded = false;

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
    if (!date) {
        return "Unknown";
    }

    return new Date(date).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
}

function getSelectedPrediction() {
    if (!selectedContract || !socialData) {
        return null;
    }

    for (const prediction of socialData.contract_predictions) {
        if (prediction.ticker === selectedContract.ticker) {
            return prediction;
        }
    }

    return null;
}

function selectContract(contract, button) {
    const yes = Math.round(contract.yes_price * 100);
    const no = 100 - yes;

    selectedContract = contract;
    yesPrice.textContent = yes + "%";
    noPrice.textContent = no + "%";
    yesBar.style.width = yes + "%";
    noBar.style.width = no + "%";
    eventStatus.textContent = contract.status;
    eventVolume.textContent = formatVolume(contract.volume);
    contractClose.textContent = formatDate(contract.close_time);
    eventUpdated.textContent = formatDate(contract.observed_at);
    kalshiLink.href = contract.url;

    for (const contractButton of contractButtons.children) {
        contractButton.classList.remove("contract-button--selected");
    }

    button.classList.add("contract-button--selected");
    showComparison();
    showDiscussion();
}

function showComparison() {
    if (!socialData) {
        return;
    }

    const prediction = getSelectedPrediction();

    if (!prediction || prediction.social_probability === null) {
        comparisonMarket.textContent = "--";
        comparisonSocial.textContent = "--";
        comparisonMarketBar.style.width = "0";
        comparisonSocialBar.style.width = "0";
        comparisonGap.textContent = "Unavailable";
        comparisonExplanation.textContent = "Social prediction is unavailable for this contract.";
        return;
    }

    const market = Math.round(selectedContract.yes_price * 100);
    const social = prediction.social_probability;
    const gap = social - market;

    comparisonMarket.textContent = market + "%";
    comparisonSocial.textContent = social + "%";
    comparisonMarketBar.style.width = market + "%";
    comparisonSocialBar.style.width = social + "%";

    if (gap > 0) {
        comparisonGap.textContent = "+" + gap + " pts";
        comparisonExplanation.textContent = "Social posts expect this more — it may be underpriced.";
    } else if (gap < 0) {
        comparisonGap.textContent = "−" + Math.abs(gap) + " pts";
        comparisonExplanation.textContent = "The market expects this more — it may be overpriced.";
    } else {
        comparisonGap.textContent = "0 pts";
        comparisonExplanation.textContent = "Social posts and the market agree on this outcome.";
    }
}

function showDiscussion() {
    if (!socialData) {
        return;
    }

    const prediction = getSelectedPrediction();

    if (!prediction) {
        discussionList.textContent = "Discussion is unavailable for this contract.";
        return;
    }

    if (!prediction.party) {
        discussionList.textContent = "Discussion is available at party level, not candidate level.";
        return;
    }

    if (!discussionLoaded) {
        return;
    }

    if (!discussionPosts.length) {
        discussionList.textContent = "No discussion found.";
        return;
    }

    discussionList.innerHTML = "";

    for (const post of discussionPosts) {
        const agrees = post.supported_party === prediction.party;
        const card = document.createElement("article");
        const header = document.createElement("div");
        const author = document.createElement("p");
        const badge = document.createElement("p");
        const body = document.createElement("div");
        const text = document.createElement("p");
        const metadata = document.createElement("div");
        const details = document.createElement("p");

        card.className = "discussion-card card";
        header.className = "discussion-card__header";
        author.className = "discussion-card__author";
        badge.className = "badge " + (agrees ? "badge--positive" : "badge--negative");
        body.className = "discussion-card__body";
        metadata.className = "discussion-card__metadata";

        author.textContent = post.author;
        badge.textContent = agrees ? "Supports " + prediction.party : "Against " + prediction.party;
        text.textContent = post.text;
        details.textContent = post.like_count + " likes · " + formatDate(post.created_at);

        header.append(author, badge);
        body.appendChild(text);
        metadata.appendChild(details);
        card.append(header, body, metadata);
        discussionList.appendChild(card);
    }
}

function showContracts(contracts) {
    contractButtons.innerHTML = "";

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

    if (contracts.length) {
        selectContract(contracts[0], contractButtons.children[0]);
    }
}

function updateStickyBorder() {
    if (window.scrollY >= contractSwitcher.offsetTop) {
        contractSwitcher.classList.add("contract-switcher--stuck");
    } else {
        contractSwitcher.classList.remove("contract-switcher--stuck");
    }
}

function loadEvent() {
    fetch("/api/events/" + eventTicker)
        .then(function (response) {
            return response.json();
        })
        .then(function (event) {
            eventTitle.textContent = event.display_name;
            kalshiLink.href = `https://kalshi.com/markets/${eventTicker.toLowerCase()}`;
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
}

function loadSocialData() {
    fetch("/api/events/" + eventTicker + "/social")
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            socialData = data;
            coverageSource.textContent = data.coverage.source;
            coveragePosts.textContent = data.coverage.posts_analyzed.toLocaleString();
            coverageAuthors.textContent = data.coverage.unique_authors.toLocaleString();
            coveragePredictions.textContent = data.directional_prediction_count.toLocaleString();
            showComparison();
            showDiscussion();
            loadDiscussion();
        })
        .catch(function () {
            comparisonGap.textContent = "Social data unavailable";
            coverageSource.textContent = "Unavailable";
            coveragePosts.textContent = "Unavailable";
            coverageAuthors.textContent = "Unavailable";
            coveragePredictions.textContent = "Unavailable";
            discussionList.textContent = "Discussion unavailable.";
        });
}

function loadDiscussion() {
    fetch("/api/events/" + eventTicker + "/social/posts")
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            discussionPosts = data.posts;
            discussionLoaded = true;
            showDiscussion();
        })
        .catch(function () {
            discussionList.textContent = "Discussion unavailable.";
        });
}

window.addEventListener("scroll", updateStickyBorder);
updateStickyBorder();
loadEvent();
loadSocialData();
