# Finance
CS50x's Finance with some custom features

## Get Started
Finance is a web app that simulates the tradings in a stocks market. It enables the user to sell and buy stocks based on it's real value and names, which is accomplished through API calls, manage it's extract and buget in real time, as it's stocks values vary. In order to run this application, I suggest you to use the [CS50 IDE](https://ide.cs50.io/), which is avaiable for free and have it's enviroment setted with all requirements to accomplish this right away.

After you create an account, clone this repository with

`git clone https://github.com/William-Fernandes252/Finance.git`

Set the API key with

`export API_KEY=pk_4aa1910b7dd040309b1a50c51ef4ceaa`

And finally run the application with

`flask run`

## Custom Features
As custom features (besides the features required in the course), I implemented: 
  - A **Cart** functionality, where the users can select and buy multiple stocks all at once;
  - A **Favorites** functionality, where the users can follow the stocks prices and add them to cart as they want;
  - A **cash managment** system, where the users can add or withdraw money in their accounts;
  - A interface to **edit** usernames and passwords.
