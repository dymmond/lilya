from lilya.app import Lilya

# Creates the application instance with app_name and version set
# and loads the remaining parameters from the Settings
app = Lilya(
    debug=True,
    middleware=...,
    permissions=...,
)
