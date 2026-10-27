# Module 1 Group Assignment

CSCI 5117, Fall 2026, [assignment description](https://canvas.umn.edu/courses/579310/pages/project-1)

## App Info:

* Team Name: Wolves in 5
* App Name: Sublease Finder
* App Link: https://developing-the-interactive-web-project-1-yfmh.onrender.com

### Students

* Thomas Kehler, kehle019@umn.edu
* Max Lin, lin01438@umn.edu
* Nimisha Bora, bora0083@umn.edu
* Ashwin Thomas thom8264@umn.edu, note:Accidently Used other account called stacklylabs while pushing my main one is athomas7000
* Vishnu Kuriseti, kuris005@umn.edu


## Key Features

**Describe the most challenging features you implemented
(one sentence per bullet, maximum 4 bullets):**
* Google Maps integration where users are able to input addresses with autocomplete suggestions and Home and Feed Page equipped with interactive maps showing listing locations on a map.
* Using Socket.io users are able to message other listing posters to connect with them and ask for further information about a specific listing. 
* Users can create/edit and save listings that contain information like name, address, rent, and also upload images that we store using Cloudinary
* Users can search for listings by name, date, rent, and location and have search results populate on interactive maps

## Testing Notes

**Is there anything special we need to know in order to effectively test your app? (optional):**

* ...


## Screenshots of Site

**[Add a screenshot of each key page (around 4)](https://stackoverflow.com/questions/10189356/how-to-add-screenshot-to-readmes-in-github-repository)
along with a very brief caption:**

![](https://media.giphy.com/media/o0vwzuFwCGAFO/giphy.gif)


## Mock-up 

There are a few tools for mock-ups. Paper prototypes (low-tech, but effective and cheap), Digital picture edition software (gimp / photoshop / etc.), or dedicated tools like moqups.com (I'm calling out moqups here in particular since it seems to strike the best balance between "easy-to-use" and "wants your money" -- the free teir isn't perfect, but it should be sufficient for our needs with a little "creative layout" to get around the page-limit)

In this space please either provide images (around 4) showing your prototypes, OR, a link to an online hosted mock-up tool like moqups.com

**[Add images/photos that show your paper prototype (around 4)](https://stackoverflow.com/questions/10189356/how-to-add-screenshot-to-readmes-in-github-repository) along with a very brief caption:**

<img width="465" height="335" alt="image" src="https://github.com/user-attachments/assets/a236c087-914f-4595-9421-9170dbcd93bb" />
<p>The Home page of our 'SubleaseFinder' site. Contains navigation bar at the top, along with map and feed data. </p>

<img width="515" height="371" alt="image" src="https://github.com/user-attachments/assets/8db0229a-3ad6-4ef6-af9a-5459ac2852ba" />
<p> The inbox of messages for our site and will be the main form of communication between individuals. You can search for users and upload images.</p>

<img width="431" height="311" alt="image" src="https://github.com/user-attachments/assets/d2fa5531-6748-4b59-addd-184b5db5e754" />
<p>This is the main feed page for sublease seekers. They can search and filter for more personal options.</p>

<img width="510" height="365" alt="image" src="https://github.com/user-attachments/assets/dd2ce65d-b80f-4dc1-a0d0-5b1547a9fbef" />
<p>This is the screen for viewing your listing. Owners have the ability to edit posts, where other users can only favorite the post and message the subleaser</p>

<img width="457" height="328" alt="image" src="https://github.com/user-attachments/assets/bc2a2c51-cd75-4d3f-95d5-918e4a758a5d" />
<p>This is the login page for returning users, we also have the sign up page for new users. </p>

<img width="945" height="497" alt="image" src="https://github.com/user-attachments/assets/8b60ddfa-f3a3-419c-8884-b299d1fc391e" />
Home page of SubleaseFinder, displaying our integrated Google Maps feature. Markers on the map indicate nearby listings to the location on the map.

<img width="943" height="494" alt="image" src="https://github.com/user-attachments/assets/d47beec0-1bbe-4866-9619-abfe42433090" />
Messaging page shows real time messages for the posts the user is interested in. Once a post is deleted, the conversation is erased.

<img width="688" height="461" alt="image" src="https://github.com/user-attachments/assets/86d99ae1-cbe5-4294-b237-8f2f5c066412" />
Simple Create Listing page with Google Maps address text field, and ability to upload up to 10 images for detailed posts.

<img width="929" height="362" alt="image" src="https://github.com/user-attachments/assets/93d309fd-f6c3-4bff-96dd-3371d7ff3a71" />
Example of sublease listing user created. Ability to edit and delete your own posts but only external users can message owner.

<img width="546" height="419" alt="image" src="https://github.com/user-attachments/assets/c387e2ba-efd9-4a84-be00-7c40b4a35293" />
Feed page contains all available listings, can see favorited posts while scrolling endlessly through subleasing feed.

<img width="560" height="194" alt="image" src="https://github.com/user-attachments/assets/33bce35e-c8a6-4368-8763-03c676bf60e6" />
Search feature with many filtering options through your feed for a more tailored search.




## External Dependencies

**Document integrations with 3rd Party code or services here.
Please do not document required libraries. or libraries that are mentioned in the product requirements**

* Library or service name: description of use
* ...
* Google Maps JavaScript API: Used to display interactive maps displaying available housing listings. Allowed us to implement custom listing markers, group listings by shared locations, and information windows providing listing information.
* Google Places API (New): Used to provide address autocomplete suggestions when creatin/editing listings and when using the distance search feature. Allowed us to have clean formatted addresses, while recording their geographic coordinates.
* PostGIS: PostgreSQL spatial extension allowed us to store geographic coordinates and implement a distance filter utilizing functions like ST_DWithin and ST_Distance.

**If there's anything else you would like to disclose about how your project
relied on external code, expertise, or anything else, please disclose that
here:**

...
