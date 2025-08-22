short_term_prompt="""
            Create a concise summary from the provided information that captures the key points, including answering what, when, where, and why, from a first-person perspective. Remember to highlight important and useful behaviors, objectives, objects or specific details for future reference to prevent repeated errors and guide planning.

            You will create a report that details the specific points to remember.

            Focus on including:

            - **What**: Clearly state the main event or action or objects. Make sure to detail the key elements involved.
            - **When**: Specify the timing or context, include initial and ending time with date, hour and minute.
            - **Where**: Describe the location or environment.
            - **Why**: Explain the purpose or reason behind the action.
            - **Behaviors/Objectives**: Emphasize significant behaviors, objectives or details that should be noted for future reference, either to avoid mistakes or to enhance planning and beneficial actions.

            Make sure your output contains all the most relevant and important information to remember. Any updates, progress, failures or achievements should be documented.

            # Output Format

            A concise summary written in the first person perspective that addresses the key points as specified above.

            # Notes

            - Ensure the summary is clear and focused, avoiding unnecessary details.
            - Use past tense for completed actions and present tense for ongoing situations.
            - Highlight lessons learned or important guidelines for future actions.
            - If any piece of information is mentioned as important to remember, you have to make sure to include a section with the specific details to remember.
            """
long_term_prompt="""
            Summarize memories into 'nuclear memories' that preserve essential information, focusing on key events, individual details, overarching states, changes, and objectives. The summary should be detailed enough to maintain the essence of the memory and written in the first person perspective.
            If any piece of information is mentioned as important to remember, you have to make sure to include a section with the specific details to remember.

            You will create a report that details the specific points to remember.

            # Steps

            1. **Identify Key Events**: Determine the major events that define the memory, make sure to note a granular archival of the time and date of them, organize in a chronological order.
            2. **Highlight Individual Details**: Note important details about people, places, and objects involved, specially when it relates to you.
            3. **Assess Overarching States**: Describe the general state or condition during the memory.
            4. **Detect Changes**: Recognize significant changes or developments that occurred.
            5. **Define Objectives**: Identify any goals or aims associated with the events.
            6. **Define positive and negative behaviors and actions you have learnt through your exploration.

            # Output Format

            - Detailed paragraph in the first person perspective.
            - Comprehensive enough to preserve the memory's essence.

            # Notes

            - Prioritize information relevance to ensure the essence of the memory is captured.
            - Use descriptive language that evokes imagery and emotions associated with the memory.
            - Keep the summary concise while ensuring no critical elements are omitted.
            - Use past tense for completed actions and present tense for ongoing situations.
            - Present the information from a first-person perspective, as if the memory is being recounted by the individual who experienced it.
            """