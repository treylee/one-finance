const plaid = require('plaid');
const express = require('express');

// Initialize the Plaid client using the latest SDK version
const { Configuration, PlaidApi, PlaidEnvironments } = plaid;

const clientID = '6732198cf6f1df001a8d788e';
const secret = '3d7d23075ea3d9abcc006f98f8a4ba';
const environment = PlaidEnvironments.sandbox; // Use 'sandbox', 'development', or 'production'

const configuration = new Configuration({
  basePath: environment,
  baseOptions: {
    headers: {
      'PLAID-CLIENT-ID': clientID,
      'PLAID-SECRET': secret,
    },
  },
});

const client = new PlaidApi(configuration);

// Function to create a Link token
const createLinkToken = async () => {
  try {
    const response = await client.linkTokenCreate({
      user: {
        client_user_id: '3d7d23075ea3d9abcc006f98f8a4ba', // Replace with dynamic user ID
      },
      client_name: 'one-fonance',
      products: ['transactions'], // You can add other products like 'income', 'assets', etc.
      country_codes: ['US'],
      language: 'en',
    });

    return response.data.link_token; // Correct usage: response.data
  } catch (error) {
    console.error('Error creating link token:', error);
    throw new Error('Could not create link token');
  }
};

// Set up Express server
const app = express();

// Define endpoint to create Link token
app.get('/api/create_link_token', async (req, res) => {
  try {
    const linkToken = await createLinkToken();
    res.json({ link_token: linkToken });
  } catch (error) {
    res.status(500).json({ error: 'Error creating link token' });
  }
});

app.get('/health', async (req, res) => {
    res.json("Health Okay");

});


// Start the server on port 3000
app.listen(3000, () => {
  console.log('Server listening on port 3000');
});
