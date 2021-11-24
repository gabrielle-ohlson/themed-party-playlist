# backend for web app

# `Flask` is what we will use to instantiate our application, and `render_template` is what we will use to connect the HTML we wrote above to our application.
from flask import Flask, render_template

# We must now create our app, which I will store in a variable called `app`:
app = Flask(__name__)

# Now, we need to deal with routing — a route is a URL pattern, i.e. the base URL of your website would have the route of `/`, whereas another route within your website may have the path `/route_path`. Since our application only has one page, we will only need to write a function for the `/` route. To specify the route, we use a decorator above our function with the form `@app.route(route_path)`. The function currently does nothing, as we just added a pass to the body.
@app.route("/")
def index():
	# Load current count
	f = open("count.txt", "r")
	count = int(f.read())
	f.close()

	# Increment the count
	count += 1

	# Overwrite the count
	f = open("count.txt", "w")
	f.write(str(count))
	f.close()

	# Render HTML with count variable
	return render_template("index.html", count=count)


# Run application
if __name__ == "__main__":
	app.run()