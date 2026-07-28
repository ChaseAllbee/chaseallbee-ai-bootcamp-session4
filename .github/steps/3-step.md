## Step 3: Solve issues with Agent Mode and GitHub MCP Server

Great work doing that research and finding potential consulting platform enhancements.
Not only did we find some new ideas to help manage consulting capabilities, but we did all that quickly too.

Plenty of time to focus on the fun stuff, like serving our awesome clients and growing our consultants' skills! 🌱

On that note, it seems the practice leads have also been active.
Looks like they submitted some capability enhancement requests! Perfect! 🚀

Now, let's use our MCP server's tools and Copilot to do a bit of triage and get some work done.

### :keyboard: Activity: Easily implement an important issue

1. Ensure the **Copilot Chat** panel is open and **Agent** mode is selected. Verify the MCP server tools are also still available.

1. Ask Copilot about the open issues on this repository.

   > ![Static Badge](https://img.shields.io/badge/-Prompt-text?style=social&logo=github%20copilot)
   >
   > ```prompt
   > How many open issues are there on my repository?
   > ```

   > 🪧 **Note:** Check that the List Issues tool is called with proper parameters.

1. Ask Copilot to summarize the important issues.

   > ![Static Badge](https://img.shields.io/badge/-Prompt-text?style=social&logo=github%20copilot)
   >
   > ```prompt
   > Oh no. That's too many for me! Please get the list of issues,
   > review the descriptions and comments, and pick the top 3 most important.
   > ```

   <details>
   <summary> <b> 💡 Tip:</b> Pre-authorize tool usage</summary><br/>

   If Copilot uses a tool often, you can proactively grant permission for the rest of the conversation session.

   <img width="350" src="https://github.com/user-attachments/assets/d741191e-4d98-489d-92d2-f1069fd6c34e"/>

   </details>

1. Review the suggested issues. If Copilot didn't give a specific recommendation, try providing some feedback to narrow the results.

1. With the list narrowed, ask Copilot to implement an issue. **Byte can't determine if the changes work, just that an attempt was made.**

   > ![Static Badge](https://img.shields.io/badge/-Prompt-text?style=social&logo=github%20copilot)
   >
   > ```prompt
   > #codebase Let's do the first one. Follow these steps:
   > 1. Checkout a new local branch for making our changes.
   > 2. Make the changes then confirm with me that they look correct.
   > 3. Push the changes and start a pull request.
   > ```

   > ⚠️ **Warning:** Always verify the actions Copilot is asking to perform, especially with the external abilities provided by an MCP server, which probably have no undo option.

1. Once the pull request is created, Byte will start checking your work. Give them a moment and keep watch of the comments. You will see Byte respond with progress info and the next step!

### 🧪 Bonus Activity: Quality Engineering (QE) Path

In addition to implementing the feature, you can also explore the Quality Engineering path:

1.  **Explore the Tests**: Ask Copilot to explain the current test setup in the `tests/` folder.
2.  **Fix the Failing Test**: There is a placeholder failing test in `tests/test_capabilities.py`. Ask Copilot to help you implement the missing feature (filtering) OR update the test to match the current behavior.
3.  **Add New Tests**: Ask Copilot to generate new integration tests for the API endpoints.

> ![Static Badge](https://img.shields.io/badge/-Prompt-text?style=social&logo=github%20copilot)
>
> ```prompt
> @workspace I want to work on the Quality Engineering track. 
> Please help me update the test automation:
> 1. Fix the failing test `test_capability_filter_implementation` in `tests/test_capabilities.py` by implementing the logic in `src/app.py`.
> 2. Add a new test case to `tests/test_capabilities.py` that verifies the `/capabilities` endpoint.
> ```

> **Note:** If you modify any files in the `tests/` folder, Byte (the lab bot) will detect your QE work and run a special validation check on your Pull Request!

<details>
<summary>Having trouble?</summary><br/>

- If tools are not being requested, verify your MCP configuration is correct.
- If Copilot cannot retrieve results, verify you are using this Codespace's token or a Personal Access Token (PAT) with appropriate permissions. By default, the codespace token we are using only has access to this repository.

</details>
