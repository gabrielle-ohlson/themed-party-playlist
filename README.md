# Themed Party Playlist: Spotify AI

Web application written in Python using `flask` and deployed on Heroku.

Basic flask/heroku setup informed by [this](https://github.com/venkatesannaveen/sample-webapp) repo (detailed tutorial for that code can be found on 'towardsdatascience' [here](https://towardsdatascience.com/create-and-deploy-a-simple-web-application-with-flask-and-heroku-103d867298eb)).


## Debug

Activate virtual environment with command: `source spotify/bin/activate`

deactivate with command: `deactivate` lol

kill the localhost with command: `npx kill-port 5000`

update 'requirements.txt' with command: `pip freeze > requirements.txt`\
*(but make sure to replace*
```
torch==1.10.0
torchtext==0.11.0
```
with
```
-f https://download.pytorch.org/whl/torch_stable.html
torch==1.10.0+cpu
```
 *for heroku performance/storage reasons)*

## TODO:
- [ ] make sign in page look nice
- [x] add customization options if certain form elements are chosen
<<<<<<< HEAD
- [ ] add spinning record player
=======
<<<<<<< HEAD
- [ ] add spinning record player
=======
>>>>>>> e5a40e0de6eeec7a7ae72a8827bbde8319080ffb
>>>>>>> cf40ebbe8bff257e0a04b47b7522acabc446ae78
- [ ] test out NLTK vs torchtext