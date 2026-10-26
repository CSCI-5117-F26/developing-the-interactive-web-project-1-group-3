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
    for (const group of Object.values(groupings)) {
        const marker = new AdvancedMarkerElement({
            map: map,
            position: {
                lat: group[0].lat,
                lng: group[0].lng
            },
            title: `${group.length} listing(s)`
        });
    }
}