window.initMap = async function () {
    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    const map = new Map(document.getElementById("home-map"), {
        center: { lat: 44.975, lng: -93.235 },
        zoom: 13,
        mapId: "Home_Map"
    });

    for (const listing of mapListings) {
        // for now skip lisitngs w null coords
        if (listing.lat == null || listing.lng == null) {
            continue;
        }
        new AdvancedMarkerElement({
            map: map,
            position: {
                lat: listing.lat,
                lng: listing.lng
            },
            title: listing.title
        });
    }
};