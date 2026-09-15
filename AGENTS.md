## Business Requirements

- An MVP which will accept Suricata alert data in the form of JSON and inscert it into a PostgresQL database.
- Additional tables and fields need to be added for allowing a user to categorized the alerts, create categorizations, and to audit users work.
- The alerts will be presented on a web UI
- The web UI will need user accouts for access
- The web UI needs a configuration page allowing user management, categorization creation, and managing auto categorizations of alerts (Autocats).
- The web UI should allow for multiple users and indicate when other users are focused on a specific alert.
- The web UI should show a scrolling pagenated list of alerts and when the user clicks on one of the alerts the details of the alret show below.
- Once an alert has been categorized it should drop off the list on the web UI.
- Categorizations of alerts need to track date of categorization and the user who categorized the alert.
- Reports need to be generated for the following: rules with more than one categorization, rules under each categorization, list of rules autocategorized and their details.
- There needs to be an agent/service built to forward the alert logs from the alert.json file on the Suricata device to the database backend. 

## Technical Details
- Use Apache as the web service
- nginx can be used as the connector for the suricata to database and the web UI to apache
- The the agent/service on the Suricata box should be written in Rust
- The OS on all systems will be Ununtu
- The backend system needs to be built as a docker container with connected storage for persistance
- Suricata agent/service with connect to backend using tcp/7754

## Strategy
1. Write plan with success criteria for each phase to be checked off. Include project scaffolding, including .gitignore, and rigorous unit testing.
2. Do not execute the plan until it has been verified.

## Coding Standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal and update as changes are made. IMPORTANT: no emojis ever