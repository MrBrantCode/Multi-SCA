const express = require("express");
const axios = require("axios");
const chalk = require("chalk");
require("dotenv").config();

const app = express();
app.get("/", async (_req, res) => {
  try {
    const r = await axios.get("https://example.com");
    res.send(chalk.green(`OK: ${r.status}`));
  } catch (e) {
    res.status(500).send(chalk.red(String(e)));
  }
});

app.listen(3000, () => {
  console.log("listening on 3000");
});


