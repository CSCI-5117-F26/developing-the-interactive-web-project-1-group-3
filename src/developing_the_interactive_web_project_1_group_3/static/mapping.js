window.initMap = async function () {
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } =
        await google.maps.importLibrary("marker");

    const map = new Map(document.getElementById("home-map"), {
        center: { lat: 44.975, lng: -93.235 },
        zoom: 13,
        mapId: "DEMO_MAP_ID"
    });
    displayListings(map, mapListings, AdvancedMarkerElement);
};

function displayListings(map, listings, AdvancedMarkerElement) {
    const groupings = {};
    // groupings to handle same location listings
    for (const listing of listings) {
        if (listing.lat == null || listing.lng == null) {
            continue;
        }
        const key = `${listing.lat},${listing.lng}`;
        if (!groupings[key]) {
            groupings[key] = [];
        }
        groupings[key].push(listing);
    }
    // create one marker per grouping
    const infoWindow = new google.maps.InfoWindow();
    for (const group of Object.values(groupings)) {
        const marker = new AdvancedMarkerElement({
            map: map,
            position: {
                lat: group[0].lat,
                lng: group[0].lng
            },
            title: `${group.length} listing(s)`
        });
        
        // generate html content for the information window
        const content = document.createElement("div");
        for (const listing of group) {
            const row = document.createElement("div");
            const title = document.createElement("h2");
            title.textContent =listing.title;
            const rent =document.createElement("p");
            rent.textContent = `$${listing.rent}/month`;
            const link = document.createElement("a");
            link.href = listing.url;
            link.textContent = "View Listing";
            link.className ="pure-button pure-button-primary";
            row.append(title, rent, link);
            content.appendChild(row);
        }
        //only one popup at a time
        marker.addListener("click", () => {
            infoWindow.setContent(content);
            infoWindow.open({
                anchor: marker,
                map: map
            });
        });
    }
}