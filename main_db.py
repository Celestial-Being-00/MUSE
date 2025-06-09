from zhipuai import ZhipuAI
import json
import re
import os
from datetime import datetime
import time
import mysql.connector

# connect database
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "story_generator",
    "pool_size": 20,
    "pool_name": "story_pool",
    "pool_reset_session": True
}

pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)


class StoryManager:
    def __init__(self):
        self.stories = {}
        self.current_section = {}

    def save_log(self, request_msg, response_msg):


        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"save error: {str(e)}")
            db_connection.rollback()
        finally:

            cursor.close()
            db_connection.close()


    def save_story(self, content, theme):
        if theme not in self.stories:
            self.stories[theme] = []
        self.stories[theme].append(content)

    def get_previous_stories(self, theme):
        return "\n\n".join(self.stories.get(theme, []))


class StoryGenerator:
    def __init__(self, client):
        self.client = client
        self.story_theme = ""
        self.genre_style = {}
        self.background = {}
        self.core_plot = {}
        self.characters = {}
        self.plot_planning = {}
        self.narrative_style = {}
        self.writing_guide = WritingGuide()
        self.current_plot_planning = ""
        self.is_completed = False
        self.completion_reason = ""

    def save_log(self, request_msg, response_msg):

        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"save error: {str(e)}")
            db_connection.rollback()
        finally:

            cursor.close()
            db_connection.close()


    def get_story_theme(self):
        self.story_theme = input("please enter premise：")
        return self.story_theme

    def extract_plot_planning(self, writing_guide):
        """
        Extract plot planning content from the writing guide, supporting dictionary input format

        Args:
            writing_guide: Can be a dictionary (containing plot_planning key) or a string

        Returns:
            Dictionary containing formatted plot planning
        """
        # Initialize default return result
        result = {
            "plot_planning": {
                "scene": {
                    "location": "",
                    "characters": [],
                    "mood": "",
                    "action": ""
                },
                "dynamic_outline": {},
                "current_progress": ""
            }
        }

        try:
            # If it's a dictionary type, extract the plot_planning field
            plot_planning_text = ""
            if isinstance(writing_guide, dict):
                if "plot_planning" in writing_guide:
                    plot_planning_text = writing_guide["plot_planning"]
                else:
                    print("plot_planning field not found in dictionary")
                    return result
            else:
                # If it's a string type, use it directly
                plot_planning_text = writing_guide

            # Ensure plot_planning_text is a string
            if not isinstance(plot_planning_text, str):
                return result

            # Extract scene setting
            scene_pattern = r'####\s*Scene Setting\s*([\s\S]*?)(?=####|\Z)'
            scene_match = re.search(scene_pattern, plot_planning_text)
            if scene_match:
                scene_text = scene_match.group(1).strip()

                # Extract core location
                location_pattern = r'\*\*Core Location\*\*:\s*(.*?)(?=\n|\r|$)'
                location_match = re.search(location_pattern, scene_text)
                if location_match:
                    result["plot_planning"]["scene"]["location"] = location_match.group(1).strip()

                # Extract appearing characters
                characters_pattern = r'\*\*Appearing Characters\*\*:\s*(.*?)(?=\n|\r|$)'
                characters_match = re.search(characters_pattern, scene_text)
                if characters_match:
                    characters_text = characters_match.group(1).strip()
                    result["plot_planning"]["scene"]["characters"] = [c.strip() for c in characters_text.split(',')]

                # Extract scene tone/mood
                mood_pattern = r'\*\*Scene Tone\*\*:\s*(.*?)(?=\n|\r|$)'
                mood_match = re.search(mood_pattern, scene_text)
                if mood_match:
                    result["plot_planning"]["scene"]["mood"] = mood_match.group(1).strip()

            # Extract current section plot development
            action_pattern = r'####\s*Current Section Plot Development\s*([\s\S]*?)(?=####|\Z)'
            action_match = re.search(action_pattern, plot_planning_text)
            if action_match:
                result["plot_planning"]["scene"]["action"] = action_match.group(1).strip()

            # Extract dynamic outline
            outline_pattern = r'####\s*Dynamic Outline\s*([\s\S]*?)(?=####|\Z)'
            outline_match = re.search(outline_pattern, plot_planning_text)
            if outline_match:
                outline_text = outline_match.group(1).strip()

                # Use regular expressions to extract all events
                event_pattern = r'\*\*Event\s*(\d+)\*\*:\s*([\s\S]*?)(?=\*\*Event|\Z)'
                event_matches = re.finditer(event_pattern, outline_text)

                dynamic_outline = {}
                for match in event_matches:
                    event_num = match.group(1).strip()
                    event_text = match.group(2).strip()
                    dynamic_outline[event_num] = event_text

                result["plot_planning"]["dynamic_outline"] = dynamic_outline

            # Extract current story progress
            progress_pattern = r'####\s*Current Story Progress\s*([\s\S]*?)(?=####|\Z)'
            progress_match = re.search(progress_pattern, plot_planning_text)
            if progress_match:
                progress_text = progress_match.group(1).strip()
                # Modificación importante: cambiar el patrón para que capture tanto "to" como "at"
                progress_num_pattern = r'Current progress (?:to|at): Event\s*(\d+)'
                progress_num_match = re.search(progress_num_pattern, progress_text)
                if progress_num_match:
                    result["plot_planning"]["current_progress"] = progress_num_match.group(1).strip()

            return result

        except Exception as e:
            import traceback
            print(f"Failed to parse plot planning: {str(e)}")
            print(traceback.format_exc())
            return result

    @staticmethod
    def filter_writing_guidelines(text):
        """
        Filter writing guide content, removing the "3. Core Plot Planning" section and
        "### 5. Current Section Plot Planning" section.
        Deletion range starts from the specified title and continues until the next title
        (e.g., starting with a number or special identifier) is encountered.

        Parameters:
            text (str): Original writing guide text

        Returns:
            str: Filtered writing guide text
        """
        # Remove "3. Core Plot Planning" section:
        filtered = re.sub(
            r"(?ms)^3\.\s*Core Plot Planning[:]?.*?(?=^(?:###\s*5\.|\d+\.)\s*)",
            "",
            text
        )
        # Remove "### 5. Current Section Plot Planning" section:
        filtered = re.sub(
            r"(?ms)^###\s*5\.\s*Current Section Plot Planning[:]?.*?(?=^\d+\.\s*)",
            "",
            filtered
        )
        # Clean up extra blank lines
        filtered = re.sub(r'\n\s*\n', '\n\n', filtered).strip()
        return filtered

    def generate_story_content(self, guide_dict):
        """Main method for generating story content (using comparison functionality rather than review)"""
        try:
            print("\n=== Starting story generation ===")
            # Generate initial story, handle the returned result directly as a string
            raw_story = self._generate_initial_story(guide_dict)
            print(f"Initial story length: {len(raw_story)}")

            # Set up checking and optimization agents
            structure_agent = StructureEditor(self.client)
            emotional_agent = EmotionalOrchestrator(self.client)
            style_agent = LiteraryStylist(self.client)
            reader_agent = ReaderAdvocateAgent(self.client)
            suggestion_editor = SuggestionEditor(self.client)
            editor_agent = StoryEditorAgent(self.client)

            # Only make one optimization attempt
            max_attempts = 1
            final_story = raw_story

            for attempt in range(max_attempts):
                print(f"\n=== Optimization attempt {attempt + 1} ===")

                # Get evaluation results from four experts
                structure_result = structure_agent.check_story(final_story, guide_dict)
                emotional_result = emotional_agent.check_story(final_story)
                style_result = style_agent.check_story(final_story, guide_dict)
                reader_result = reader_agent.check_story(final_story, guide_dict)

                # Integrate expert suggestions
                integrated_suggestions = suggestion_editor.integrate_suggestions(
                    structure_result,
                    emotional_result,
                    style_result,
                    reader_result
                )

                print("\n" + "=" * 40)
                print(f"Integrated suggestions: {integrated_suggestions['integrated_suggestions']}")
                print(f"Priority improvement areas: {', '.join(integrated_suggestions['priority_areas'])}")
                print("=" * 40 + "\n")

                # Execute story revision
                revised_story = self.execute_story_revision(
                    final_story,
                    integrated_suggestions,
                    guide_dict
                )
                print(f"Revised story: {revised_story}")
                print(f"Revised story length: {len(revised_story)}")
                print(f"Character count change: {len(revised_story) - len(final_story)}")

                # Compare original story and revised story
                comparison_result = editor_agent.compare_stories(final_story, revised_story)

                # Choose the final story based on comparison results
                if comparison_result["selected_version"] == "A":
                    print("\nOriginal story quality is better, keeping original version")
                    print(
                        f"Verdict result: Original story wins {comparison_result['a_wins']}:{comparison_result['b_wins']}")
                    print(f"Verdict details: {comparison_result['verdict_details']}")
                    print(f"Verdict explanation: {comparison_result['explanation']}")
                    # Continue using original story
                else:
                    print("\nRevised story quality is better, adopting revised version")
                    print(
                        f"Verdict result: Revised story wins {comparison_result['b_wins']}:{comparison_result['a_wins']}")
                    print(f"Verdict details: {comparison_result['verdict_details']}")
                    print(f"Verdict explanation: {comparison_result['explanation']}")
                    final_story = revised_story

            print("\nGenerating final chapter title...")
            title_response = self.generate_story_title(final_story)
            title = title_response if isinstance(title_response, str) else title_response.get('title',
                                                                                              'Untitled Chapter')
            return {
                'content': final_story,
                'title': title
            }

        except Exception as e:
            print(f"Error occurred while generating story content: {str(e)}")
            import traceback
            traceback.print_exc()  # Print detailed error information
            return {
                'content': f"Story generation failed: {str(e)}",
                'title': 'Error Chapter'
            }

    def execute_story_revision(self, raw_story, integrated_suggestions, guide_dict):
        """
        Simplified method to enhance story quality based on integrated suggestions
        Focuses on one high-quality revision rather than multiple iterations
        """
        writing_guide = guide_dict.get('content', '')

        # Extract the core event of the current section
        core_event = self.extract_plot_planning(writing_guide)['plot_planning']['scene']['action']

        prompt = f"""As a creative story optimization expert, please enhance the story based on the following information:

        === Core Event of Current Section (must be preserved) ===
        {core_event}

        === Original Story ===
        {raw_story}

        === Integrated Revision Suggestions ===
        {integrated_suggestions['integrated_suggestions']}

        === Priority Improvement Areas ===
        {', '.join(integrated_suggestions['priority_areas'])}

        === Optimization Guidelines ===
        1. Boldly improve the story content without being overly constrained by the original expression
        2. Make substantial improvements addressing issues identified in the integrated revision suggestions
        3. Pay special attention to priority improvement areas, ensuring notable enhancements in these aspects
        4. Significantly enhance sensory details and atmosphere in scene descriptions
        5. Deepen character emotional expressions and inner world portrayal
        6. Optimize dialogue to make it more vivid and distinctive
        7. Flexibly adjust narrative rhythm and expression style to improve reading experience
        8. While keeping the core event unchanged, feel free to rethink the perspective and details

        === Mandatory Restrictions ===
        1. Must focus on the events described in the current section, without deviating from this scope
        2. Must not introduce major characters or key plot twists not included in the original event description
        3. Must not foreshadow future plot points or flashback to past events not mentioned in the original text
        4. Maintain the basic time, location, and core storyline of the story

        Please provide a comprehensive and deep optimization of the story, making it more engaging, emotionally richer, more vivid in detail, and more beautifully expressed. Don't be afraid to make bold changes, but the core event must remain consistent. The purpose of optimization is to create a version with significantly improved quality, not just superficial decoration.

        Please return the English optimized story in JSON format:
        {{
            "content": "Optimized story content"
        }}"""

        system_message = "You are an outstanding story optimization expert, skilled at enhancing a story's expressiveness, emotional depth, and narrative charm. Please provide a high-quality story optimization based on professional evaluation feedback."

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                response_content = response.choices[0].message.content.strip()

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, response_content)

                # Clean code blocks
                if response_content.startswith("```json"):
                    response_content = response_content.replace("```json", "", 1)
                elif response_content.startswith("```"):
                    response_content = response_content.replace("```", "", 1)

                if response_content.endswith("```"):
                    response_content = response_content[:-3].strip()

                # Try to parse JSON
                try:
                    data = json.loads(response_content)
                    if "content" in data:
                        return data["content"]
                except json.JSONDecodeError:
                    # If JSON parsing fails, try using regex to extract the content part
                    content_match = re.search(r'"content"\s*:\s*"((?:\\.|[^"\\])*)"', response_content)
                    if content_match:
                        # Extract content and handle escape characters
                        extracted_content = content_match.group(1)
                        extracted_content = extracted_content.replace('\\"', '"').replace('\\\\', '\\')
                        if len(extracted_content) > 100:
                            return extracted_content

                    # If regex also fails, but content length is reasonable and looks like a story, return directly
                    if len(response_content) > 200 and "in" in response_content and "." in response_content:
                        return response_content

            except Exception as e:
                print(f"Story optimization attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("Proceeding to next attempt...")

        # All attempts failed, return original story
        print("All optimization attempts failed, returning original story")
        return raw_story

    def _generate_initial_story(self, guide_dict):
        """Generate initial story (with outline constraints), expanding the current section's story planning in detail"""
        writing_guide = guide_dict.get('content', '')

        plot_planning = self.extract_plot_planning(writing_guide)['plot_planning']
        current_scene = plot_planning['scene']

        # Get current section number and next section content
        current_progress = plot_planning.get('current_progress', '1')
        dynamic_outline = plot_planning.get('dynamic_outline', {})

        # Convert to integer for calculation
        try:
            current_progress_num = int(current_progress)
        except ValueError:
            current_progress_num = 1

        # Get next section content (if exists)
        next_section_num = str(current_progress_num + 1)
        next_section_content = dynamic_outline.get(next_section_num, "No next section content")

        # Build boundary prompt
        boundary_prompt = f"""
        === Story Boundary Guidance (to help you understand the scope of the current section) ===
        Current section (Section {current_progress}) content:
        {dynamic_outline.get(current_progress, "Current section content unavailable")}

        Next section (Section {next_section_num}) will describe (but should NOT be included in the current section):
        {next_section_content}

        Note: Your task is limited to describing the current section in detail, and must not introduce plot developments from the next section.
        """

        prompt = f"""#
        Please write a detailed story scene focused exclusively on the current section's events. Your task is to expand on the current section's events in detail, not to create new plots or introduce unmentioned characters.

        === Current Section Events (must strictly adhere to this scope) ===
        {current_scene}

        {boundary_prompt}

        === Character Restrictions (highest priority rules) ===
        1. You may only use characters explicitly mentioned in the current section events, introducing any other characters is prohibited
        2. Before writing, carefully analyze the current section events text to identify all character names explicitly mentioned
        3. If a character is not explicitly mentioned in the current section events, they absolutely cannot appear in your story, even if they appear in character profiles in the guide

        === Content Requirements ===
        1. Enrich the story with details, specifically describing the environment, character actions, dialogue, psychological activities, and scene atmosphere
        2. Make the story more vivid, visual, and authentic
        3. You may reference the theme, style, and background settings from the writing guide
        4. All content must directly serve the development of the current section events, without deviating from the main theme

        === Style Reference (for reference only, do not introduce new characters) ===
        {self.filter_writing_guidelines(writing_guide)}

        === Strictly Prohibited ===
        1. Strictly forbidden to introduce any characters not mentioned in the current section events, whether protagonists, supporting characters, or antagonists
        2. Strictly forbidden to add plot developments beyond the scope of current section events or backstory
        3. Strictly forbidden to plant foreshadowing or hint at future event developments
        4. Strictly forbidden to include events or plots that will happen in the next section, especially not to introduce characters or actions from the next section prematurely

        Please return the English story content in JSON format, example:
        {{"content": "Story text content"}}"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system",
                         "content": "You are a professional writer. Your task is to strictly expand the story based on the current section events, without introducing any characters or plots not mentioned in the current section events. You must ensure not to exceed the scope of the current section, and not to introduce content from the next section prematurely. Please output the story text content in English JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.95
                )
                raw_content = response.choices[0].message.content.strip()

                full_request_msg = f"{"You are a professional writer. Your task is to strictly expand the story based on the current section events, without introducing any characters or plots not mentioned in the current section events. You must ensure not to exceed the scope of the current section, and not to introduce content from the next section prematurely. Please output the story text content in English JSON format."} {prompt}"

                self.save_log(full_request_msg, raw_content)

                # Remove Markdown code block markers
                if raw_content.startswith("```"):
                    raw_content = re.sub(r'^```(?:json)?\n', '', raw_content)
                    if raw_content.endswith("```"):
                        raw_content = raw_content[:-3].strip()

                print(f"Initial story content:\n{raw_content}")
                try:
                    data = json.loads(raw_content, strict=False)
                    if isinstance(data, dict) and "content" in data:
                        return data["content"]
                except Exception as e:
                    print("JSON parsing failed:", e)
                return raw_content
            except Exception as e:
                print(f"Generation failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("Regenerating...")
                    continue
                return "Generation failed"
        return "Generation failed"

    def generate_story_title(self, story_content):
        """Generate a title based on story content, return the content of the title field in JSON format"""
        if not self.client:
            print("Warning: No API client provided, using default title")
            return "Untitled Chapter"

        system_message = (
            "You are a professional story creation consultant.\n"
            "Please generate an engaging title for this story chapter. The title should be concise and powerful, accurately reflecting the main content of this chapter.\n"
            "Note:\n"
            "1. The returned result must be in strict English JSON format, formatted as follows: {\"title\": \"title content\"}\n"
            "2. The title should only include the title itself, without any additional explanation\n"
            "3. Do not use any punctuation marks\n"
            "4. Use concise phrases or short sentence forms\n"
        )

        prompt = f"""Please generate a title for the following story content:

    Story content:
    {story_content}

    Requirements:
    1. The title should highlight important content of this section
    2. Moderate length, recommended to be within 6-8 words
    3. Attractive and tense, accurately reflecting the core plot of this chapter
    Please return the title strictly in English JSON format, example format: {{"title": "title content"}}"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                raw_content = response.choices[0].message.content.strip()

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_content)

                print(f"Title:\n{raw_content}")

                # If the returned content contains Markdown code block markers, remove them
                if raw_content.startswith("```"):
                    raw_content = raw_content.replace("```json", "").replace("```", "").strip()

                # Try to parse JSON and extract "title"
                try:
                    data = json.loads(raw_content)
                    if isinstance(data, dict) and "title" in data:
                        return data["title"]
                except Exception as e:
                    print(f"JSON parsing error: {e}")

                # If parsing fails, return the original text directly
                if raw_content and len(raw_content) >= 3:
                    return raw_content
                else:
                    print("Generated title does not meet expectations, regenerating...")
            except Exception as e:
                print(f"Title generation failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("Regenerating...")
                    continue
                else:
                    return "Untitled Chapter"
        return "Untitled Chapter"

    def analyze_genre_and_style(self, max_retries=3):
        system_message = """You are a professional story creation consultant. Please output analysis results in English JSON format.
        Return strictly according to the specified format, do not include any additional content."""

        prompt = f"""Analyze this story premise: {self.story_theme}

        Please return the premise analysis results in the following English JSON format:

        {{
            "genre": "Story type (such as fantasy, romance, etc.)",
            "style": "Narrative style (such as light and cheerful, serious and profound, suspenseful and tense, etc.)"
        }}"""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content


                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)


                json_match = re.search(r'\{[^{]*\}', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    json_str = json_str.strip()
                    json_str = re.sub(r'[\n\r\t]', '', json_str)
                    json_str = re.sub(r',\s*}', '}', json_str)

                    try:
                        analysis = json.loads(json_str)
                        if 'genre' in analysis and 'style' in analysis:
                            self.genre_style = analysis
                            formatted_output = self.format_analysis_output(analysis)

                            # update writing guide
                            self.writing_guide.update_section('genre_style', formatted_output)

                            return formatted_output
                    except json.JSONDecodeError:
                        if attempt == max_retries - 1:
                            return "Error: Unable to parse the returned JSON format"
                        continue

            except Exception as e:
                if attempt == max_retries - 1:
                    return f"error：{str(e)}"
                continue

        return "Unable to get a properly formatted response"

    def format_analysis_output(self, analysis):
        output = "1. Genre and Style:\n\n"
        output += f"- Story type: {analysis['genre']}\n"
        output += f"- Narrative style: {analysis['style']}\n"
        return output

    def generate_background(self, max_retries=3):

        system_message = """You are a World Builder - an expert focusing on the consistency and richness of background settings.
        You create based on Secondary World Theory, pioneered by J.R.R. Tolkien and further developed by Mark J.P. Wolf, focusing on how to create engaging fictional worlds:
        1. Internal consistency - the world must follow its own established rules and logic
        2. Completeness - the world should have complete history, geography, culture, and social structure
        3. Balance of uniqueness and familiarity - balance between innovative elements and elements that audiences can understand
        4. Infrastructure links - elements of the world interconnect to form an organic whole
        5. Ontological independence - the fictional world can exist independently of the main narrative

        Please output analysis results strictly in English JSON format, without adding any additional explanations."""
        prompt = f"""As a World Builder, please design a story world that conforms to Secondary World Theory based on the following information:
        Story premise: {self.story_theme}
        Story type: {self.genre_style['genre']}
        Narrative style: {self.genre_style['style']}

        Please create a world background with internal consistency, completeness, and balance of unique and familiar elements, ensuring that all elements are organically connected to form a credible secondary world.

        Please return strictly according to the following English JSON format, ensuring that the return is valid JSON:
        {{
            "world_setting": {{
                "time_period": "Specific description of the time period background",
                "environment": "Specific description of the environment",
                "social_structure": "Specific description of the social structure"
            }},
            "rules_and_systems": {{
                "core_rules": "Specific description of core rules",
                "limitations": "Specific description of limitations",
                "special_elements": "Specific description of special settings"
            }}
        }}"""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                try:

                    background = json.loads(result)
                    if 'world_setting' in background and 'rules_and_systems' in background:
                        self.background = background
                        formatted_output = self.format_background_output(background)

                        # update writing guide
                        self.writing_guide.update_section('background', formatted_output)

                        return formatted_output
                except json.JSONDecodeError:

                    json_match = re.search(r'\{[\s\S]*\}', result)
                    if json_match:
                        try:
                            json_str = json_match.group()

                            json_str = re.sub(r'```json|```', '', json_str)
                            json_str = json_str.strip()
                            background = json.loads(json_str)
                            if 'world_setting' in background and 'rules_and_systems' in background:
                                self.background = background
                                formatted_output = self.format_background_output(background)

                                self.writing_guide.update_section('background', formatted_output)

                                return formatted_output
                        except json.JSONDecodeError:
                            if attempt == max_retries - 1:
                                return "Error: Unable to parse the returned JSON format"
                            continue

            except Exception as e:
                if attempt == max_retries - 1:
                    return f"An error occurred：{str(e)}"
                continue

        return "Unable to get a properly formatted response"

    def format_background_output(self, background):
        output = "2. Background Setting:\n"
        output += "\nWorld View:\n"
        world = background['world_setting']
        output += f"- Time period: {world['time_period']}\n"
        output += f"- Environment: {world['environment']}\n"
        output += f"- Social structure: {world['social_structure']}\n"

        output += "\nRules and Settings:\n"
        rules = background['rules_and_systems']
        output += f"- Core rules: {rules['core_rules']}\n"
        output += f"- World limitations: {rules['limitations']}\n"
        output += f"- Special settings: {rules['special_elements']}"
        return output

    def generate_core_plot(self, max_retries=3):
        system_message = """You are a Narrative Architect - an expert responsible for designing the overall structure of the story.
        You create based on Dramatic Arc Theory, which divides the story into five key stages:
        1. Setup: Introduction of characters, environment, and basic situation
        2. Rising: Development stage of conflict and complexity
        3. Climax: Turning point or peak of tension
        4. Falling: Events leading to resolution after the climax
        5. Ending: Final results and closure of plot threads

        Please output analysis results strictly in English JSON format, without adding any additional explanations."""
        prompt = f"""As a Narrative Architect, please design a core plot that follows Dramatic Arc Theory based on the following information:
        Story premise: {self.story_theme}
        Story style: {self.genre_style}
        World view: {self.background}

        Please use the five stages of Dramatic Arc Theory (Setup, Rising, Climax, Falling, Ending) to design an engaging story development path.
        The main story content of each stage needs to be described in detail, and the transition markers between each stage must be clear and definite, as these markers will be used to determine the current stage of the story.

        Please return strictly according to the following English JSON format, ensuring that the return is valid JSON:
        {{
            "main_goal": {{
                "objective": "The protagonist's core goal",
                "motivation": "Motivation for pursuing the goal"
            }},
            "core_conflict": {{
                "main_obstacle": "Main obstacle",
                "antagonist": "Description of the opposing force"
            }},
            "plot_stages": {{
                "setup": "Specific story content of the setup stage",
                "rising": "Specific story content of the rising conflict stage",
                "climax": "Specific story content of the climax stage",
                "falling": "Specific story content of the falling conflict stage",
                "ending": "Specific story content of the ending stage"
            }},
            "stage_markers": {{
                "to_rising": "Marker event for entering the rising stage",
                "to_climax": "Marker event for entering the climax stage",
                "to_falling": "Marker event for entering the falling stage",
                "to_ending": "Marker event for entering the ending stage",
                "story_end": "Marker event for the end of the story"
            }}
        }}"""

        for attempt in range(max_retries):
            try:

                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )
                result = response.choices[0].message.content

                json_str = re.search(r'\{[\s\S]*\}', result).group()
                json_str = re.sub(r'```json|```', '', json_str).strip()

                core_plot_data = json.loads(json_str)

                self.core_plot_raw = core_plot_data
                self.core_plot = core_plot_data

                if self._validate_plot_structure(core_plot_data):
                    formatted_output = self.format_core_plot_output(core_plot_data)
                    self.writing_guide.update_section('core_plot', formatted_output)
                    return formatted_output
                else:
                    print("[Warning] 数据结构不完整，但已保存原始数据")
                    return "生成的核心情节结构不完整，请重试"

            except (json.JSONDecodeError, AttributeError, KeyError) as e:
                print(f"JSON解析失败（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
                if attempt == max_retries - 1:
                    return "错误：无法解析返回的JSON格式"
                continue

            except Exception as e:
                print(f"发生未知错误（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
                if attempt == max_retries - 1:
                    return f"发生错误：{str(e)}"
                continue

        return "无法获得正确格式的响应"

    def _validate_plot_structure(self, plot):
        """验证情节结构的完整性"""
        required_keys = {
            'main_goal': ['objective', 'motivation'],
            'core_conflict': ['main_obstacle', 'antagonist'],
            'plot_stages': ['setup', 'rising', 'climax', 'falling', 'ending'],
            'stage_markers': ['to_rising', 'to_climax', 'to_falling', 'to_ending', 'story_end']
        }

        try:
            for main_key, sub_keys in required_keys.items():
                if main_key not in plot:
                    return False

                if sub_keys:  # 如果有子键需要检查
                    if main_key == 'plot_stages' or main_key == 'stage_markers':
                        if not all(k in plot[main_key] for k in sub_keys):
                            return False
                    else:
                        if not all(k in plot[main_key] for k in sub_keys):
                            return False

            return True
        except Exception:
            return False

    def format_core_plot_output(self, plot):
        """Format core plot output"""
        output = "3. Core Plot Planning:\n\n"

        # Main goal
        output += "Main Goal:\n"
        output += f"- Core objective: {plot['main_goal']['objective']}\n"
        output += f"- Motivation: {plot['main_goal']['motivation']}\n\n"

        # Core conflict
        output += "Core Conflict:\n"
        output += f"- Main obstacle: {plot['core_conflict']['main_obstacle']}\n"
        output += f"- Opposing force: {plot['core_conflict']['antagonist']}\n\n"

        # Plot development stages
        output += "Core Plot Development Stages:\n"
        output += f"- Setup stage: {plot['plot_stages']['setup']}\n"
        output += f"- Rising stage: {plot['plot_stages']['rising']}\n"
        output += f"- Climax stage: {plot['plot_stages']['climax']}\n"
        output += f"- Falling stage: {plot['plot_stages']['falling']}\n"
        output += f"- Ending stage: {plot['plot_stages']['ending']}\n\n"

        # Stage transition markers
        output += "Stage Transition Markers:\n"
        output += f"- Entering rising stage: {plot['stage_markers']['to_rising']}\n"
        output += f"- Entering climax stage: {plot['stage_markers']['to_climax']}\n"
        output += f"- Entering falling stage: {plot['stage_markers']['to_falling']}\n"
        output += f"- Entering ending stage: {plot['stage_markers']['to_ending']}\n"
        output += f"- Story ending marker: {plot['stage_markers']['story_end']}\n\n"

        return output

    def generate_characters(self, max_retries=3):

        system_message = """You are a Character Designer - an expert responsible for the rationality of character motivation and development.
        You create based on Character Arc Theory, which focuses on how characters undergo psychological and behavioral evolution in the story:
        1. Initial state - the character's beliefs, values, and behavior patterns at the beginning
        2. Desires and needs - the distinction between the character's superficial pursuit and true inner needs
        3. Internal and external conflicts - external challenges and inner contradictions faced by the character
        4. Transformation catalyst - key events or realizations that prompt character change
        5. Growth trajectory - how the character gradually evolves from the initial state to the final state

        Please output analysis results strictly in English JSON format, without adding any additional explanations.
        """

        prompt = f"""As a character psychologist, please design characters with deep psychological motivations and growth potential based on the following information:
        Story premise: {self.story_theme}
        Story style: {self.genre_style}
        background setting: {self.background}

        When designing each character, please ensure:
        1. The character has a clear psychological state and behavior pattern
        2. The character has internal motivations and potential conflicts that drive the story
        3. The character has space for development and transformation, laying the foundation for subsequent character arcs

        Please return ONLY the following English JSON format, with ONLY these fields and nothing more, Do not add any additional fields to the character objects. Only include name, role_type, and background:

        {{
            "characters": [
                {{
                    "name": "Character name",
                    "role_type": "Character type (protagonist/antagonist/supporting character)",
                    "background": "A brief introduction to the character's background (about 50 words)"
                }}
            ]
        }}
        """

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                print(f"Character generation result: {result}")
                print(f"Character generation attempt {attempt + 1}/{max_retries}")

                # 移除代码块标记
                cleaned_result = re.sub(r'```(?:json)?|```', '', result).strip()

                # 提取JSON对象
                json_match = re.search(r'(\{[\s\S]*\})', cleaned_result)
                if json_match:
                    json_str = json_match.group(1)

                    # 替换智能引号
                    json_str = json_str.replace('"', '"').replace('"', '"')

                    # 尝试方法1: 使用正则表达式直接提取字符数据，绕过JSON解析
                    characters = {"characters": []}
                    try:
                        # 查找characters数组
                        array_match = re.search(r'"characters"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
                        if array_match:
                            chars_str = array_match.group(1)

                            # 查找每个字符对象的开始和结束
                            char_blocks = []
                            open_braces = 0
                            start_idx = None

                            for i, char in enumerate(chars_str):
                                if char == '{' and open_braces == 0:
                                    start_idx = i
                                    open_braces += 1
                                elif char == '{':
                                    open_braces += 1
                                elif char == '}':
                                    open_braces -= 1
                                    if open_braces == 0 and start_idx is not None:
                                        char_blocks.append(chars_str[start_idx:i + 1])
                                        start_idx = None

                            # 处理每个字符块
                            for block in char_blocks:
                                # 提取名称
                                name_match = re.search(r'"name"\s*:\s*"(.*?)"', block, re.DOTALL)
                                role_match = re.search(r'"role_type"\s*:\s*"(.*?)"', block, re.DOTALL)
                                bg_match = re.search(r'"background"\s*:\s*"(.*?)"', block, re.DOTALL)

                                if name_match and role_match and bg_match:
                                    name = name_match.group(1).replace('"', "'")
                                    role = role_match.group(1)
                                    background = bg_match.group(1).replace('"', "'")

                                    characters["characters"].append({
                                        "name": name,
                                        "role_type": role,
                                        "background": background
                                    })

                        if characters["characters"]:
                            self.characters = characters
                            formatted_output = self.format_characters_output(characters)
                            self.writing_guide.update_section('characters', formatted_output)
                            return formatted_output

                    except Exception as regex_error:
                        print(f"Regex extraction failed: {str(regex_error)}")

                    # 尝试方法2: 修复JSON字符串，替换所有名称和背景中的双引号
                    try:
                        # 使用更复杂的正则表达式处理JSON字符串中的值
                        fixed_json = json_str

                        # 先处理name字段
                        name_pattern = r'"name"\s*:\s*"(.*?)"'
                        for match in re.finditer(name_pattern, fixed_json):
                            value = match.group(1)
                            # 如果发现值中有双引号，就替换成单引号
                            if '"' in value:
                                fixed_value = value.replace('"', "'")
                                fixed_json = fixed_json.replace(f'"name": "{value}"', f'"name": "{fixed_value}"')

                        # 再处理background字段
                        bg_pattern = r'"background"\s*:\s*"(.*?)"'
                        for match in re.finditer(bg_pattern, fixed_json):
                            value = match.group(1)
                            if '"' in value:
                                fixed_value = value.replace('"', "'")
                                fixed_json = fixed_json.replace(f'"background": "{value}"',
                                                                f'"background": "{fixed_value}"')

                        # 移除非ASCII字符
                        fixed_json = re.sub(r'[^\x00-\x7F]+', ' ', fixed_json)

                        # 尝试加载修复后的JSON
                        characters = json.loads(fixed_json)
                        if 'characters' in characters and len(characters['characters']) > 0:
                            self.characters = characters
                            formatted_output = self.format_characters_output(characters)
                            self.writing_guide.update_section('characters', formatted_output)
                            return formatted_output

                    except json.JSONDecodeError as e:
                        print(f"Fixed JSON parsing also failed: {str(e)}")
                        print(f"Problematic JSON string: {fixed_json}")

                    # 所有方法都失败了
                    if attempt == max_retries - 1:
                        return "Error: Unable to parse the returned JSON format after multiple attempts"
                    continue
                else:
                    print(f"No JSON object found in response on attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        return "Error: Unable to find JSON object in the response"
                    continue

            except Exception as e:
                print(f"General error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return f"An error occurred: {str(e)}"
                continue

        return "Unable to get a correctly formatted response"

    def format_characters_output(self, characters_data):
        """Format character settings output"""
        output = "4. Character Settings:\n"

        for char in characters_data['characters']:
            output += f"\n## {char['name']} ({char['role_type']})\n\n"

            # Character background
            output += "### Background\n"
            output += f"{char['background']}\n"

        return output

    def generate_plot_planning(self, max_retries=3):
        """Generate dynamic outline and plot plan for current section"""
        print("Start generating dynamic outline...")

        try:
            # generate dynamic outline (directly based on five story stages)
            dynamic_outline = self._generate_dynamic_outline(max_retries)
            print(f"outline generated,{len(dynamic_outline)} detailed event")

            # get current event description
            event_1 = dynamic_outline.get("1", "no description")
            print(f"event1 description：{event_1}")

            current_progress = "1"

            # generate scene planning based on current event description
            plot_planning_data = self._generate_scene_planning(event_1, max_retries)

            if plot_planning_data and "plot_planning" in plot_planning_data:
                plot_planning_data["plot_planning"]["dynamic_outline"] = dynamic_outline
                plot_planning_data["plot_planning"]["current_progress"] = current_progress

                # 保存结果并更新撰写指南
                self.plot_planning = plot_planning_data["plot_planning"]
                formatted_output = self.format_plot_planning_output(plot_planning_data)
                self.writing_guide.update_section("plot_planning", formatted_output)
                return formatted_output

            return "Unable to get plot planning response in the correct format"

        except Exception as e:
            import traceback
            print(f"Failed to generate dynamic outline：{str(e)}")
            print(traceback.format_exc())
            return f"Failed to generate dynamic outline：{str(e)}"

    def _generate_dynamic_outline(self, max_retries=3):
        """Generate a dynamic outline based on a three-layer structure and optimize through multiple rounds of iterations:
        1. Generate a main event framework
        2. Generate sub-events for each main event
        3. Generate detailed events for each sub-event
        4. Improve outline quality through multiple rounds of iterations
        """
        # save the current outline structure
        all_events = {}
        event_counter = 1
        outline_structure = {}  # save the outline structure

        print("Start generating dynamic outline...")

        # phase 1: generate main event framework
        print("\nGenerate main event framework...")

        system_message = (
            "You are a professional creative story consultant. Please output your results in English JSON format."
            "Strictly follow the specified format."
        )

        main_prompt = f"""Based on the following information:

        Story premise: {self.story_theme}
        Story style: {self.genre_style}
        World view: {self.background}
        Story characters: {self.characters}

        Write a concise high-level outline for this story, formatted as follows:

        1. [Plot event 1]
        2. [Plot event 2]
        ...

        There should be at most 4 events (beginning, middle, end).

        Important: Use complete sentences and correct punctuation. Each sentence should end with a single period. Do not use ellipses (three dots "...").

        Please return the results in English JSON format as follows:
        {{
            "main_events": [
                {{
                    "event": "Plot event description"
                }},
                ...
            ]
        }}"""

        main_events_result = self._make_api_request(
            system_message,
            main_prompt,
            "main_events",
            max_retries
        )

        main_events_list = []
        if isinstance(main_events_result, dict):

            if "main_events" in main_events_result:
                main_events_list = main_events_result["main_events"]
            else:

                main_events_list = list(main_events_result.values())
        elif isinstance(main_events_result, list):

            main_events_list = main_events_result
        else:
            print("Error: Unable to parse primary event result")
            return {}

        print("Successfully generated the main event:")

        for i, main in enumerate(main_events_list[:4]):

            if isinstance(main, dict) and "event" in main:
                main_event_text = main["event"]
            else:
                main_event_text = str(main)

            main_num = i + 1
            main_key = f"{main_num}. {main_event_text}"
            print(f"- {main_key}")

            outline_structure[main_key] = {}

            # Generate sub-events for this main event
            sub_prompt = f"""Based on the following information:

            Story premise: {self.story_theme}
            Story style: {self.genre_style}
            World view: {self.background}
            Story characters: {self.characters}

            Current main event:
            {main_key}

            Using one or two numbers (and keeping in mind each main event has up to 4 sub-events), please describe the event details of the current main event.

            Important: Use complete sentences and correct punctuation. Each sentence should be a complete event statement. Do not use ellipses (three dots "...").

            Please return the results in English JSON format as follows:
            {{
                "sub_events": [
                    {{
                        "event": "Sub-event description"
                    }},
                    {{
                        "event": "Sub-event description"
                    }}
                ]
            }}"""

            sub_events_result = self._make_api_request(
                system_message,
                sub_prompt,
                "sub_events",
                max_retries
            )

            sub_events_list = []
            if isinstance(sub_events_result, dict):
                if "sub_events" in sub_events_result:
                    sub_events_list = sub_events_result["sub_events"]
                else:
                    sub_events_list = list(sub_events_result.values())
            elif isinstance(sub_events_result, list):
                sub_events_list = sub_events_result

            if not sub_events_list:
                print(f"Error: Unable to generate sub-events for main event '{main_key}'")
                continue

            # Handle each sub-event
            for j, sub in enumerate(sub_events_list[:4]):
                # Make sure sub is in dictionary form or convert it to a dictionary
                if isinstance(sub, dict) and "event" in sub:
                    sub_event_text = sub["event"]
                else:
                    sub_event_text = str(sub)

                sub_letter = chr(97 + j)  # a, b, c, d
                sub_key = f"{sub_letter}. {sub_event_text}"

                # Create entries for sub-events
                outline_structure[main_key][sub_key] = {}

                # Generate detailed events for this sub-event
                detail_prompt = f"""Based on the following information:

                Story premise: {self.story_theme}
                Story style: {self.genre_style}
                World view: {self.background}
                Story characters: {self.characters}

                Main event:
                {main_key}
                    Sub-event:
                    {sub_key}

                Using one or two numbers (and keeping in mind each sub-event has up to 4 detailed events), please describe the event details of the current sub-event.

                Important: Use complete sentences and correct punctuation. Each sentence should be a complete event statement. Do not use ellipses (three dots "...").

                Please return the results in English JSON format as follows:
                {{
                    "detailed_events": [
                        {{
                            "event": "Detailed event description"
                        }},
                        {{
                            "event": "Detailed event description"
                        }}
                    ]
                }}"""

                # Generate detailed events
                detail_events_result = self._make_api_request(
                    system_message,
                    detail_prompt,
                    "detailed_events",
                    max_retries
                )

                # Handling responses in different formats
                detailed_events_list = []
                if isinstance(detail_events_result, dict):
                    if "detailed_events" in detail_events_result:
                        detailed_events_list = detail_events_result["detailed_events"]
                    else:
                        detailed_events_list = list(detail_events_result.values())
                elif isinstance(detail_events_result, list):
                    detailed_events_list = detail_events_result

                if not detailed_events_list:
                    print(f"Error: Unable to generate detail event for sub-event '{sub_key}'")
                    continue

                # Process each detailed event
                for k, detail in enumerate(detailed_events_list[:4]):
                    # Make sure detail is in dictionary form or convert it to a dictionary
                    if isinstance(detail, dict) and "event" in detail:
                        detail_event_text = detail["event"]
                    else:
                        detail_event_text = str(detail)

                    # use roman numerals for the first 4 details
                    roman_numerals = {0: "i", 1: "ii", 2: "iii", 3: "iv"}
                    roman = roman_numerals.get(k, f"detail{k + 1}")
                    detail_key = f"{roman}. {detail_event_text}"

                    # Add to the outline structure
                    outline_structure[main_key][sub_key][detail_key] = ""

                    # Add to the all events list
                    all_events[str(event_counter)] = detail_event_text
                    event_counter += 1

        # Add the detailed events to the outline structure
        print("\nGenerated three-layer structure outline:")
        for main_key, main_value in outline_structure.items():
            print(main_key)
            for sub_key, sub_value in main_value.items():
                print(f"  {sub_key}")
                for detail_key in sub_value.keys():
                    print(f"    {detail_key}")

        print(f"\nA total of {event_counter - 1} detailed events were collected")

        original_outline_text = ""
        for event_id, event_text in all_events.items():
            original_outline_text += f"event{event_id}: {event_text}\n\n"

        print(f"All the detailed events of the second phase: {original_outline_text}")

        story_context = {
            "premise": self.story_theme,
            "style": self.genre_style,
            "world": self.background,
            "characters": self.characters
        }

        # Phase 3: Multiple rounds of iterative optimization outline
        print("\nStart phase 3: multiple rounds of iterative optimization outline...")

        # setting the number of iterations
        ITERATION_ROUNDS = 3
        current_best_outline = all_events

        for iteration in range(1, ITERATION_ROUNDS + 1):
            print(f"\n===== The {iteration} round of iteration starts =====")

            current_outline_text = ""
            for event_id, event_text in current_best_outline.items():
                current_outline_text += f"event{event_id}: {event_text}\n\n"

            # 1. Multi-theoretical analysis agent provides advice
            print(f"1. Round {iteration} - Running multi-theory analysis agents...")
            analysis_suggestions = self._run_theory_based_agents(current_outline_text, max_retries=3)

            # 2. Integrate proxy synthesis suggestions
            print(f"2. Round {iteration} - Run the integration agent...")
            integrated_suggestion = self._run_integration_agent(analysis_suggestions, current_outline_text,
                                                                max_retries=3)

            # 3. Refactoring proxy optimization outline
            print(f"3. Round {iteration} - Run refactoring agent...")
            modified_outline = self._run_reconstruction_agent(integrated_suggestion, current_outline_text,
                                                              story_context,
                                                              current_best_outline, max_retries=3)

            # 4. Compare the current best outline with the revised outline
            print(f"4. Round {iteration} - Compare the two outline versions...")
            current_best_outline = self._compare_storylines(current_best_outline, modified_outline, story_context,
                                                            max_retries=3)

            print(f"===== The {iteration} round of iteration is completed =====")

        # The final outline is the outline after multiple rounds of iterative optimization.
        print("Phase 3 completed: The story outline has been optimized through multiple rounds of iterations")

        return current_best_outline

    def _compare_storylines(self, outline_a, outline_b, story_context, max_retries=3):
        """Compare two story outlines and select the better one"""
        print("Starting comparison of two story outline versions...")

        # Convert both outlines to text format for comparison
        outline_a_text = "Story outline A:\n\n"
        for event_id, event_text in outline_a.items():
            outline_a_text += f"Event{event_id}: {event_text}\n\n"

        outline_b_text = "Story outline B:\n\n"
        for event_id, event_text in outline_b.items():
            outline_b_text += f"Event{event_id}: {event_text}\n\n"

        # Construct comparison system prompt
        comparison_system_message = (
            "You are a professional story evaluation expert, skilled at fairly and objectively comparing the quality of different story outlines."
            "Your task is to evaluate two story outlines based on four key dimensions and return the results in strict English JSON format."
            "Do not include any additional explanations, comments, or analysis, only return the requested English JSON format."
        )

        # Construct comparison user prompt
        comparison_prompt = f"""
        Please compare the following two story outlines and evaluate their performance across four dimensions.

        premise:
        {story_context['premise']}

        Story outline A:
        {outline_a_text}
        Story outline B:
        {outline_b_text}

        Evaluation tasks:
        1) Overall, which story outline is more interesting/engaging? A / B
        2) Overall, which story outline has more coherent and compact plot? A / B
        3) Overall, which story outline is more creative? A / B
        4) Overall, which story outline is more closely related to the premise? A / B

        Please return your evaluation results in the exact English JSON format below:
        {{
          "verdict": "1:your choice, 2:your choice, 3:your choice, 4:your choice"
        }}

        Very important:
        1. Do not add any other content or explanations
        2. Maintain exact English JSON format
        3. Your choice should be A or B, do not use other symbols or words
        4. The value of the verdict field must use the exact format "1:your choice, 2:your choice, 3:your choice, 4:your choice", with no spaces between numbers and letters
        """

        # set temperature to 0
        for attempt in range(max_retries):
            try:
                print(f"Attempting to compare two outlines (attempt {attempt + 1}/{max_retries})...")

                # Directly use API, set temperature=0
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": comparison_system_message},
                        {"role": "user", "content": comparison_prompt}
                    ],
                    temperature=0.0  # Set temperature to 0 to ensure consistency of results
                )
                raw_response = response.choices[0].message.content
                print(f"Received response: {raw_response}")

                if not raw_response:
                    print(f"Comparison attempt {attempt + 1}/{max_retries} failed, API return is empty")
                    continue

                # Try to parse JSON response
                import json
                import re

                # Clean potential markdown code block markers
                cleaned_response = re.sub(r'^```(json)?|```$', '', raw_response, flags=re.MULTILINE).strip()

                # Try to match the outermost braces
                json_match = re.search(r'(\{[\s\S]*\})', cleaned_response)
                if json_match:
                    json_str = json_match.group(1)
                    try:
                        result = json.loads(json_str)
                        if "verdict" in result:
                            verdict_str = result["verdict"]
                            print(f"Successfully extracted verdict: {verdict_str}")

                            # Handle more flexible format matching, including possible spaces
                            verdict_pattern = re.compile(r'(\d)\s*:\s*([AB])')
                            matches = verdict_pattern.findall(verdict_str)

                            if matches and len(matches) == 4:
                                # Sort by question number
                                sorted_matches = sorted(matches, key=lambda x: int(x[0]))
                                verdicts = [match[1] for match in sorted_matches]

                                a_count = verdicts.count('A')
                                b_count = verdicts.count('B')

                                print(f"Comparison result: A wins {a_count} items, B wins {b_count} items")

                                # Detailed output for each dimension's winner
                                dimensions = ["Interest", "Coherence", "Creativity", "Relevance to premise"]
                                for i, winner in enumerate(verdicts):
                                    print(
                                        f"- {dimensions[i]}: {'Version A' if winner == 'A' else 'Version B'} is better")

                                # If A wins more items, choose A; if B wins more items or tie, choose B
                                if a_count > b_count:
                                    print("Final choice: Version A")
                                    return outline_a
                                else:
                                    print("Final choice: Version B")
                                    return outline_b
                            else:
                                print(
                                    f"Unable to extract complete four-dimension evaluation from verdict string: {verdict_str}")
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing error: {str(e)}")

                # If JSON parsing fails, try to extract directly from the raw response
                verdict_pattern = re.compile(r'(\d)\s*:\s*([AB])')
                matches = verdict_pattern.findall(raw_response)

                if matches and len(matches) == 4:
                    # Sort by question number
                    sorted_matches = sorted(matches, key=lambda x: int(x[0]))
                    verdicts = [match[1] for match in sorted_matches]

                    a_count = verdicts.count('A')
                    b_count = verdicts.count('B')

                    print(f"Direct pattern matching result: A wins {a_count} items, B wins {b_count} items")

                    # If A wins more items, choose A; if B wins more items or tie, choose B
                    if a_count > b_count:
                        print("Final choice: Version A")
                        return outline_a
                    else:
                        print("Final choice: Version B")
                        return outline_b
                else:
                    print("Unable to directly extract complete four-dimension evaluation from response")

            except Exception as e:
                import traceback
                print(f"Error occurred during comparison process: {str(e)}")
                print(traceback.format_exc())

        # If all attempts fail, default to version B (modified version)
        print("Comparison process failed, defaulting to Version B (modified version)")
        return outline_b

    def _run_theory_based_agents(self, outline_text, max_retries=3):
        """Run analytical agents based on different narrative theories to provide macro-level recommendations"""

        # 1. Narrative Transportation Theory Agent (Green & Brock, 2000) - Handling immersion and emotional resonance
        narrative_transportation_system_message = (
            "You are an experience design consultant working based on Narrative Transportation Theory (Green & Brock, 2000)."
            "Narrative Transportation Theory studies how stories 'transport' readers into the story world, immersing them and creating emotional resonance."
            "As an experience design consultant, your area of expertise is designing narrative experiences that fully immerse readers, as if they were actually there."
            "Your analysis focuses on evaluating the richness of details, sensory descriptions, emotional resonance points, and reader imagination space in the story, with particular attention to:"
            "1) Whether scene depictions include sufficient multi-sensory details;"
            "2) Whether character emotional experiences are expressed through concrete actions;"
            "3) Whether unexpected turning points can trigger emotional responses in readers;"
            "4) Whether the narrative rhythm helps maintain reader engagement."
            "Your task is to analyze the story outline from a macro perspective, identify important opportunities to enhance reader immersion, and provide specific suggestions."
            "You need to provide a coherent piece of text as a suggestion, rather than listing specific modifications for each event."
            "Your contribution will significantly enhance the story's immersion and emotional resonance, making readers feel as if they are present in the story."
        )

        transportation_prompt = f"""
        From a macro perspective, analyze the following story outline to identify key opportunities to enhance reader immersion and emotional connection.

        【Story Premise】
        {self.story_theme}

        【Story Outline】
        {outline_text}

        Please comprehensively evaluate the outline from the following four aspects and provide optimization suggestions:

        1. Sensory detail richness - Whether scene depictions can activate multiple senses in readers
        2. Concretization of emotional experiences - Whether character emotions are presented through concrete actions rather than descriptions
        3. Emotional impact of turning points - Whether unexpected events can trigger strong emotional responses in readers
        4. Immersive rhythm design - Whether the narrative rhythm helps readers maintain continuous engagement

        Please provide a concise macro suggestion, synthesizing the above assessments, explaining how to improve the outline as a whole to enhance the story's immersion.
        Do not provide suggestions for each specific event, but focus on the experience design of the entire story.
        Do not mention any theory or explain why to do this, just give specific suggestions directly.

        === Output Format ===
        {{
          "suggestions": "Your macro suggestion content (a coherent piece of text, do not list item-by-item suggestions)"
        }}
        """

        # 2. Cognitive Narrative Theory Agent (Herman, 2013) - Strengthen coherence and logical completeness
        cognitive_narrative_system_message = (
            "You are a narrative structure analyst working based on Cognitive Narrative Theory (Herman, 2013)."
            "Cognitive Narrative Theory studies how readers construct coherent mental models of stories, focusing on narrative logic and the completeness of causal relationships."
            "As a narrative structure analyst, your primary responsibility is to diagnose breaking points in story structure, logical gaps, and unclosed subplots."
            "Your professional analysis focuses on the following core issues:"
            "1) Whether the story's causal chain is complete, and whether there are causal breaks between events;"
            "2) Whether subplot storylines all receive appropriate closure and resolution;"
            "3) Whether character motivations are clear and consistent, and whether behaviors align with their personality and motivations;"
            "4) Whether there are redundant or repetitive events (events that are essentially similar but in different scenes also count as repetitive);"
            "5) Whether the story structure consistently serves the core theme, without introducing irrelevant subplots;"
            "6) The importance is the coherent progression of the plot, not whether scenes are repeated (the same scene can appear multiple times, as long as the plot doesn't repeat)."
            "You need to provide a coherent piece of text as a suggestion, rather than listing specific modifications for each event."
            "Your contribution will significantly enhance the story's coherence and structural integrity, enabling readers to construct a clear and complete mental model of the story."
        )

        cognitive_prompt = f"""
        From a macro perspective, strictly analyze structural issues in the following story outline, with particular attention to causal coherence, logical breaking points, and unclosed subplots.

        【Story Premise】
        {self.story_theme}

        【Story Outline】
        {outline_text}

        Please conduct an in-depth diagnosis from the following five aspects, identify all issues and provide repair suggestions:

        1. Causal chain break detection - Whether there are instances where events lack necessary connections or have excessive jumps
        2. Unclosed subplot detection - Whether there are plot elements that are introduced but not sufficiently developed and resolved (such as mysterious envelopes, recordings, etc. that appear)
        3. Character motivation inconsistency detection - Whether character behaviors consistently align with their established motivations and personalities (especially whether antagonist motivations are reasonable)
        4. Plot redundancy detection - Whether there are multiple essentially similar plots (note: the same scene can appear multiple times, as long as the plot doesn't repeat)
        5. Core theme deviation detection - Whether there are events that don't directly serve the story's central conflict and core premise

        Please pay special attention to whether any subplot (such as suddenly appearing props, mysterious elements) is introduced in the story but doesn't receive appropriate development and closure.

        Please provide a concise yet in-depth diagnostic suggestion, clearly pointing out issues that need repair. No need to reference any theory, directly give practical repair suggestions.
        Focus on structural issues that would disrupt reader understanding and immersion.

        === Output Format ===
        {{
          "suggestions": "Your narrative structure diagnosis and repair suggestions (a coherent piece of text, focusing on the most critical structural issues)"
        }}
        """

        # 3. Conceptual Blending Theory Agent (Fauconnier & Turner, 2002) - Enhance creativity
        conceptual_blending_system_message = (
            "You are a concept innovation consultant working based on Conceptual Blending Theory (Fauconnier & Turner, 2002)."
            "Conceptual Blending Theory studies how innovative ideas are produced through the fusion of different conceptual domains, focusing on innovation points that break through traditional cognitive frameworks."
            "As a concept innovation consultant, your expertise is discovering opportunities for novel concept combinations, creating unexpected story elements, with particular attention to:"
            "1) Whether there are opportunities for traditional story patterns to be subverted or recombined;"
            "2) Whether character relationships or conflict types can adopt innovative forms;"
            "3) Whether scene design can integrate unexpected elements;"
            "4) Whether plot developments can incorporate surprising yet reasonable twists."
            "Your task is to analyze the story outline from a macro perspective for opportunities for innovation, looking for points where conventional story patterns can be broken through."
            "You need to provide a coherent piece of text as a suggestion, rather than listing specific modifications for each event."
            "Your contribution will significantly enhance the story's creativity and uniqueness, making the story stand out and be memorable."
        )

        blending_prompt = f"""
        From a macro perspective, analyze the innovation space in the following story outline, looking for opportunities to break conventions and integrate new elements.

        【Story Premise】
        {self.story_theme}

        【Story Outline】
        {outline_text}

        Please comprehensively evaluate the outline from the following four aspects and provide innovation suggestions:

        1. Traditional pattern subversion points - Which traditional story patterns can be innovatively recombined or subverted
        2. Relationship and conflict innovation - How character relationships or conflicts can be presented in more novel forms
        3. Scene element fusion - How scene design can integrate unexpected but effective element combinations
        4. Twist point surprise level - How plot twists can be designed to be more unexpected yet still reasonable

        Please provide a concise macro suggestion, synthesizing the above assessments, explaining how to improve the outline as a whole to enhance the story's innovation and uniqueness.
        Do not provide suggestions for each specific event, but focus on the creative concepts and breakthrough points of the entire story.
        Do not mention any theory or explain why to do this, just give specific suggestions directly.

        === Output Format ===
        {{
          "suggestions": "Your macro suggestion content (a coherent piece of text, do not list item-by-item suggestions)"
        }}
        """

        # 4. Affective Arc Theory Agent (Reagan et al., 2016) - Emotional rhythm and thematic coherence
        affective_arc_system_message = (
            "You are an emotional rhythm consultant working based on Affective Arc Theory (Reagan et al., 2016)."
            "Affective Arc Theory analyzes emotional patterns in successful stories, studying how emotional fluctuations affect reader experience and story effectiveness."
            "As an emotional rhythm consultant, your expertise is designing optimal emotional curves, creating engaging experiences while ensuring story theme consistency."
            "You pay particular attention to the following points:"
            "1) Whether the emotional arc has clear fluctuations rather than being flat;"
            "2) Whether climax points are set in appropriate positions and have sufficient intensity;"
            "3) Whether emotional transitions are natural and smooth rather than abrupt;"
            "4) Whether the story builds sufficient suspense and tension at key moments;"
            "5) Whether the ending's emotion resonates with the core theme, showing how the protagonist resolves the core problem from the premise."
            "Your task is to analyze the emotional rhythm and thematic coherence in the story outline from a macro perspective, evaluating the effectiveness of its emotional arc."
            "You need to provide a coherent piece of text as a suggestion, rather than listing specific modifications for each event."
            "Your contribution will significantly optimize the story's emotional experience and thematic expression, giving readers a meaningful emotional journey."
        )

        affective_prompt = f"""
        From a macro perspective, analyze the emotional rhythm and thematic coherence in the following story outline, evaluating its emotional arc design and connection to the core premise.

        【Story Premise】
        {self.story_theme}

        【Story Outline】
        {outline_text}

        Please comprehensively evaluate the outline from the following six aspects and provide optimization suggestions:

        1. Emotional fluctuation design - Whether emotional intensity has obvious changes that match the story stages
        2. Climax point layout - Whether emotional climax points are set in appropriate positions and have sufficient intensity
        3. Emotional transition smoothness - Whether emotional changes are natural and have sufficient buildup
        4. Suspense and tension - Whether the story builds sufficient suspense and tension at key moments
        5. Core theme presentation - Whether the story's emotions consistently revolve around the core theme
        6. Ending resonance with premise - Whether the ending emotion clearly shows how the protagonist resolves the core problem from the premise

        Please pay special attention to whether the ending section sufficiently resonates with the story premise, showing how the protagonist resolves the core problem or conflict.

        Please provide a concise macro suggestion, synthesizing the above assessments, explaining how to improve the outline as a whole to optimize the story's emotional rhythm and thematic coherence.
        Do not provide suggestions for each specific event, but focus on the emotional arc design and thematic expression of the entire story.
        Do not mention any theory or explain why to do this, just give specific suggestions directly.

        === Output Format ===
        {{
          "suggestions": "Your macro suggestion content (a coherent piece of text, do not list item-by-item suggestions)"
        }}
        """

        # Run four agents and collect results
        agents = [
            {"name": "Narrative Transportation Theory Agent", "system": narrative_transportation_system_message,
             "prompt": transportation_prompt},
            {"name": "Cognitive Narrative Theory Agent", "system": cognitive_narrative_system_message,
             "prompt": cognitive_prompt},
            {"name": "Conceptual Blending Theory Agent", "system": conceptual_blending_system_message,
             "prompt": blending_prompt},
            {"name": "Affective Arc Theory Agent", "system": affective_arc_system_message, "prompt": affective_prompt}
        ]

        all_suggestions = {}

        for agent in agents:
            print(f"Running {agent['name']}...")

            for attempt in range(max_retries):
                try:
                    result = self._make_api_request(
                        agent['system'],
                        agent['prompt'],
                        None,  # Modified to not use specific field name, directly get the raw response
                        1  # Single attempt
                    )

                    if result:
                        # Directly use regex to extract content of suggestions field instead of complete JSON parsing
                        import re

                        # Clean possible markdown code block markers
                        cleaned_response = re.sub(r'^```(json)?|```$', '', result, flags=re.MULTILINE).strip()

                        # Try two ways to extract suggestions content
                        # 1. Try using JSON parsing (if it's valid JSON)
                        try:
                            import json
                            json_match = re.search(r'(\{[\s\S]*\})', cleaned_response)
                            if json_match:
                                json_str = json_match.group(1)
                                parsed_json = json.loads(json_str)
                                if "suggestions" in parsed_json:
                                    suggestions_content = parsed_json["suggestions"]
                                    all_suggestions[agent['name']] = suggestions_content
                                    print(f"  Successfully got suggestions from {agent['name']}")
                                    break
                        except:
                            pass  # If JSON parsing fails, continue trying regex method

                        # 2. Use regex to directly extract suggestions field (handling cases with unescaped control characters)
                        suggestions_pattern = r'"suggestions":\s*"([\s\S]*?)(?:"|$)'
                        suggestions_match = re.search(suggestions_pattern, cleaned_response)

                        if suggestions_match:
                            # Extract suggestion content and remove possible escape characters
                            suggestions_content = suggestions_match.group(1)
                            suggestions_content = suggestions_content.replace('\\n', '\n').replace('\\r', '').replace(
                                '\\"', '"')
                            all_suggestions[agent['name']] = suggestions_content
                            print(f"  Successfully got suggestions from {agent['name']} (using regex)")
                            break
                        else:
                            # If can't extract suggestions field but response is not empty, use the entire response
                            if len(cleaned_response.strip()) > 0:
                                all_suggestions[agent['name']] = cleaned_response
                                print(f"  Successfully got suggestions from {agent['name']} (using raw response)")
                                break
                            else:
                                print(
                                    f"  Warning: Attempt {attempt + 1}/{max_retries} failed to extract suggestions field")
                    else:
                        print(f"  Warning: Attempt {attempt + 1}/{max_retries} failed to get valid response")
                except Exception as e:
                    print(f"  Warning: Attempt {attempt + 1}/{max_retries} error occurred: {str(e)}")

                if attempt == max_retries - 1:
                    print(f"  Warning: Unable to get valid suggestions from {agent['name']}")
                    all_suggestions[agent['name']] = "Failed to provide valid suggestions"

        return all_suggestions

    def _run_integration_agent(self, analysis_suggestions, outline_text, max_retries=3):
        """Run the integration agent to combine all analysis recommendations"""

        # Extract all suggestions
        all_suggestions_formatted = ""
        for agent_name, suggestion in analysis_suggestions.items():
            all_suggestions_formatted += f"【{agent_name}'s Suggestion】\n{suggestion}\n\n"

        # Integration agent system message
        integration_system_message = (
            "You are a narrative system integration expert, responsible for consolidating multi-dimensional story analysis into a coordinated and consistent modification plan."
            "Your expertise is conducting comprehensive assessments of story structure, identifying and fixing key issues that might disrupt the reader's experience."
            "Your integration process follows a strict priority system:"
            "1) First fix structural issues: logical breaks, unclosed subplots, plot redundancies, and other issues that directly disrupt story understanding;"
            "2) Second enhance thematic coherence: ensure all elements serve the core theme, and the ending directly echoes the story premise;"
            "3) Then optimize emotional rhythm: adjust climax and turning points, ensure the emotional arc is complete and smooth;"
            "4) Finally enhance creative elements: add innovation on the foundation of structural integrity and thematic clarity."
            "When evaluating various suggestions, you especially focus on balancing the following dimensions:"
            "- Balance between coherence and innovation"
            "- Balance between clear themes and subtle expression"
            "- Balance between story compactness and sufficient development"
            "- Balance between emotional depth and rhythmic fluidity"
            "You must provide a coherent integrated suggestion, prioritizing the most critical story issues, rather than trying to solve all minor problems."
            "Your final suggestion must be actionable and focused, targeting the 3-5 key aspects that most need improvement in the story."
        )

        integration_prompt = f"""
        Systematically analyze the following story outline improvement suggestions from multiple experts, and integrate them into a focused modification plan.

        【Story Premise】
        {self.story_theme}

        【Story Outline】
        {outline_text}

        【Suggestions from Experts】
        {all_suggestions_formatted}

        Please use the following workflow to integrate these suggestions (but do not describe this process in your output):

        1. Core Problem Identification
           - Find key issues pointed out by multiple experts
           - Identify problems most disruptive to story understanding and experience
           - Determine logical break points that may cause reader confusion or disengagement

        2. Problem Priority Ranking
           - First priority: Structural issues (logical breaks, unclosed subplots, essentially repetitive plots)
           - Second priority: Thematic coherence issues (relevance to the core premise)
           - Third priority: Emotional rhythm and immersion issues
           - Fourth priority: Creativity and novelty issues

        3. Solution Integration
           - Propose specific and feasible modification suggestions for each key issue
           - Ensure there are no conflicts between modification suggestions
           - Ensure modifications do not create new problems
           - Focus on the 3-5 most critical improvement directions, rather than being comprehensive

        4. Focus on the following aspects
           - Subplot closure: Ensure all introduced elements (such as mysterious letters, recordings, etc.) receive appropriate development and resolution
           - Plot deduplication: Eliminate substantially repetitive plots (even if scenes differ, essentially similar plots count as repetitive)
           - Logical coherence: Fix any causal breaks or character motivation inconsistencies
           - Theme enhancement: Strengthen connection to the story premise, ensure all plots revolve around the core conflict
           - Ending resonance: Ensure the ending clearly shows how the protagonist resolves the core problem from the premise

        Please integrate these suggestions to form a concise and powerful modification plan, focusing on the most critical issues and solutions.
        Do not mention how you integrated them, and do not explain reasons, just give specific suggestions directly.

        === Output Format ===
        {{
          "suggestions": "Your integrated suggestion content (a coherent piece of text, focusing on the key aspects that most need improvement in the story)"
        }}
        """

        # Request integration analysis
        for attempt in range(max_retries):
            try:
                result = self._make_api_request(
                    integration_system_message,
                    integration_prompt,
                    None,  # Modified to not use specific field name, directly get the raw response
                    1  # Single attempt
                )

                if result:
                    # Directly use regex to extract content of suggestions field
                    import re

                    # Clean possible markdown code block markers
                    cleaned_response = re.sub(r'^```(json)?|```$', '', result, flags=re.MULTILINE).strip()

                    # Try two ways to extract suggestions content
                    # 1. Try using JSON parsing
                    try:
                        import json
                        json_match = re.search(r'(\{[\s\S]*\})', cleaned_response)
                        if json_match:
                            json_str = json_match.group(1)
                            parsed_json = json.loads(json_str)
                            if "suggestions" in parsed_json:
                                print("Successfully got integration suggestions")
                                return parsed_json["suggestions"]
                    except:
                        pass  # If JSON parsing fails, continue trying regex method

                    # 2. Use regex to directly extract suggestions field
                    suggestions_pattern = r'"suggestions":\s*"([\s\S]*?)(?:"|$)'
                    suggestions_match = re.search(suggestions_pattern, cleaned_response)

                    if suggestions_match:
                        # Extract suggestion content and remove possible escape characters
                        suggestions_content = suggestions_match.group(1)
                        suggestions_content = suggestions_content.replace('\\n', '\n').replace('\\r', '').replace('\\"',
                                                                                                                  '"')
                        print("Successfully got integration suggestions (using regex)")
                        return suggestions_content
                    else:
                        # If can't extract suggestions field but response is not empty, use the entire response
                        if len(cleaned_response.strip()) > 0:
                            print("Successfully got integration suggestions (using raw response)")
                            return cleaned_response
                        else:
                            print(
                                f"Integration attempt {attempt + 1}/{max_retries} failed to extract suggestions field")
                else:
                    print(f"Integration attempt {attempt + 1}/{max_retries} failed to get valid response")
            except Exception as e:
                print(f"Integration attempt {attempt + 1}/{max_retries} error occurred: {str(e)}")

        print("Warning: Unable to get valid integration suggestions")
        return "Maintain original structure, focus on enhancing scene details and character emotions"

    def _run_reconstruction_agent(self, integrated_suggestion, outline_text, story_context, original_events,
                                  max_retries=3):
        """Run the refactoring agent to refactor the story outline based on the integration suggestions"""

        # Reconstruction agent system message
        reconstruction_system_message = (
            "You are a reconstruction expert well-versed in story structure, skilled at optimizing story outlines based on analysis feedback."
            "Your specialty is fixing story structure issues while significantly enhancing the story's engagement and creativity."
            "In the reconstruction process, you pay special attention to the following key aspects:"
            "1) Creativity and appeal: Inject unique creative and unexpected elements into the story, ensuring each event sparks reader curiosity and interest;"
            "2) Compactness and rhythm: Eliminate redundant plots, keep the story compact and smooth, create dynamic emotional rhythm;"
            "3) Logical completeness: Fix all logical break points and unclosed subplot issues;"
            "4) Detail richness: Add vivid specific details to each event, including multi-sensory descriptions, concrete actions, and environmental atmosphere;"
            "5) Clear ending: Design a clear and powerful ending that directly echoes the core theme and story premise;"
            "6) Strong emotional conflicts: Set up high-intensity emotional conflicts in key events, giving the story more tension and depth."
            "Your reconstruction should consider the overall needs of the story, independently deciding the most appropriate number of events and structure to serve the best story effect."
            "You can boldly adjust the number of events, merge, split, or rewrite existing events, as long as the final story is more engaging."
            "You must only return the optimized events in English JSON format, without any additional explanations or text."
        )

        reconstruction_prompt = f"""
        Based on the provided modification suggestions, systematically optimize the following story outline to create an engaging, compact, coherent, and creative story.

        【Existing Story Outline】
        {outline_text}

        【Modification Suggestions】
        {integrated_suggestion}

        Related Information:
        【Story Premise】
        {story_context['premise']}
        【Story Style】
        {story_context.get('style', 'Not specified')}
        【World Background】
        {story_context.get('world', 'Not specified')}
        【Main Characters】
        {story_context.get('characters', 'Not specified')}


        Please reconstruct the story outline according to the following workflow:

        1. Creativity Enhancement and Story Appeal
           - Inject unique creative elements and unexpected twists into the story
           - Design surprising but reasonable event developments
           - Create engaging situations and conflicts
           - Add unique worldview elements or background details
           - Design unique characteristics or abilities for key characters

        2. Coherence and Compactness Optimization
           - Eliminate all redundant or repetitive plots
           - Ensure each event has a clear role in driving story development
           - Strengthen causal relationships between events, creating a smooth story development chain
           - Adjust event sequence to ensure appropriate and engaging story rhythm
           - Remove unnecessary events to make the story more compact and efficient

        3. Structural Integrity Enhancement
           - Fix all logical breaks and plot holes
           - Ensure all subplots and introduced elements receive sufficient development and closure
           - Strengthen the story's setup-development-turn-conclusion structure
           - Design clear and powerful climax points for the story
           - Ensure the ending is clear and directly echoes the story premise

        4. Emotional Depth and Character Development
           - Deepen character motivations and internal conflicts
           - Show character emotional changes through concrete actions
           - Design powerful emotional turning points
           - Ensure character behaviors are consistent with their personality and motivations
           - Show character growth or change in key events

        5. Detail Richness Enhancement
           - Add vivid sensory details to each scene
           - Use specific environmental descriptions to enhance scene immersion
           - Make events more vivid through precise action descriptions
           - Add subtle emotional hints and atmosphere creation
           - Ensure each event has sufficient details to support subsequent story creation

        Based on the story's needs, independently decide the most appropriate number of events and structure. If increasing, decreasing, or reorganizing events helps tell a better story, please adjust according to your professional judgment.
        Don't hesitate to make major changes—if parts or all of the plot need to be completely rewritten to create a better story, please rewrite without hesitation.
        Each event should be detailed enough, including specific scene descriptions, character actions, and emotional expressions, ensuring they provide rich material for subsequent story creation.

        === Output Format ===
        Please directly return all optimized events in English JSON format, using consecutive numbering as keys. Do not add any additional explanations, introduction, or conclusion.
        {{
          "1": "Optimized detailed description of the first event",
          "2": "Optimized detailed description of the second event",
          ...and so on
        }}

        Note: Your reply must only contain this JSON object, with no other content. This JSON will be directly parsed and used.
        """

        # Request outline reconstruction
        for attempt in range(max_retries):
            try:
                print(f"Sending API request to get optimized outline (attempt {attempt + 1}/{max_retries})...")
                # Get raw response
                raw_response = self._make_api_request(
                    reconstruction_system_message,
                    reconstruction_prompt,
                    None,  # Don't use specific field name, directly return the entire response
                    3
                )

                if not raw_response:
                    print(f"Reconstruction attempt {attempt + 1}/{max_retries} failed, API return is empty")
                    continue

                print("Received API response, attempting to extract JSON content...")

                # Try to clean and parse JSON
                import json
                import re

                # Clean possible markdown code block markers
                cleaned_response = re.sub(r'^```(json)?|```$', '', raw_response, flags=re.MULTILINE).strip()

                # Try to match the outermost braces
                json_match = re.search(r'(\{[\s\S]*\})', cleaned_response)
                if json_match:
                    json_str = json_match.group(1)
                    try:
                        parsed_result = json.loads(json_str)
                        if isinstance(parsed_result, dict):
                            print(f"Successfully parsed JSON as valid outline, event count: {len(parsed_result)}")
                            return {str(k): v for k, v in parsed_result.items()}
                        else:
                            print(f"Parsed JSON is not in valid story outline format")
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing error: {str(e)}")
                else:
                    print("No JSON format content found")

            except Exception as e:
                import traceback
                print(f"Reconstruction attempt {attempt + 1}/{max_retries} error occurred: {str(e)}")
                print(traceback.format_exc())

        print("Warning: Unable to get valid reconstruction outline, keeping original outline")
        # If unable to get valid reconstruction outline, return original outline
        return original_events

    def _generate_scene_planning(self, event, max_retries=3):
        """Generate scenario planning for the current section (section 1)"""
        system_message = (
            "You are a precise scene planning expert, skilled at analyzing story events and extracting key elements."
            "Your task is to accurately identify scene locations, appearing characters, and emotional tone from story events,"
            "and ensure all extracted elements come directly from the event description, without adding anything not explicitly mentioned in the events."
        )

        prompt = f"""Please analyze the following current section's story event and extract three key elements:

        Current section story event:
        {event}

        === Output Requirements ===
        Please output in strict English JSON format as follows:
        {{
            "plot_planning": {{
                "scene": {{
                    "location": "Specific location where the current section's story scene takes place",
                    "characters": ["Character 1 explicitly mentioned in the current section event", "Character 2 explicitly mentioned in the current section event",...],
                    "mood": "Emotional tone inferred from the event content"
                }}
            }}
        }}
        """

        # Create default return structure (for handling cases where all attempts fail)
        default_response = {
            "plot_planning": {
                "scene": {
                    "location": "Unspecified location",
                    "characters": ["Unspecified character"],
                    "mood": "Unspecified tone",
                    "action": event  # Directly use the original event
                }
            }
        }

        for attempt in range(max_retries):
            try:
                print(f"Attempting to generate scene planning (attempt {attempt + 1}/{max_retries})...")
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                print(f"Received scene planning response: {result}")

                # Clean result and parse JSON
                cleaned_result = re.sub(r'```(json)?|```', '', result, flags=re.DOTALL).strip()
                json_match = re.search(r'\{[\s\S]*\}', cleaned_result)

                if json_match:
                    json_str = json_match.group()
                    print(f"Extracted JSON: {json_str}")

                    try:
                        data = json.loads(json_str)

                        # Check if JSON structure meets expectations
                        if "plot_planning" in data and "scene" in data["plot_planning"]:
                            # Manually add action field, ensure using original event content
                            data["plot_planning"]["scene"]["action"] = event
                            return data
                        else:
                            print("JSON structure does not meet expectations")
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing error: {str(e)}")

            except Exception as e:
                print(f"Scene planning generation failed: {str(e)}")

            # If this is the last attempt and failed, return default structure
            if attempt == max_retries - 1:
                print(f"Maximum retry count reached, returning default structure")
                return default_response

        return default_response

    def _make_api_request(self, system_message, prompt, result_key, max_retries):
        """Send API request and process response"""
        for attempt in range(max_retries):
            try:
                print(
                    f"Sending API request for {result_key if result_key else 'raw response'} (attempt {attempt + 1}/{max_retries})...")

                # Send API request
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                print(f"Received response: {result}")

                # If no specific field needs to be extracted, return raw response
                if result_key is None:
                    return result

                # Clean result and parse JSON
                cleaned_result = re.sub(r'```(json)?|```', '', result, flags=re.DOTALL).strip()
                json_match = re.search(r'\{[\s\S]*\}', cleaned_result)

                if not json_match:
                    print(f"No valid JSON format output detected")
                    continue

                json_str = json_match.group()
                print(f"Extracted JSON: {json_str}")

                try:
                    data = json.loads(json_str)

                    if result_key not in data:
                        print(f"Returned JSON does not contain '{result_key}' key")
                        continue

                    # Get result data
                    result_data = data[result_key]

                    # Process based on data type
                    if isinstance(result_data, dict) or isinstance(result_data, list) or isinstance(result_data, str):
                        # Support dictionary, list and string types
                        return result_data
                    else:
                        print(f"Error: API returned unexpected data type: {type(result_data)}")
                        continue

                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")
                    continue

            except Exception as e:
                import traceback
                print(f"API request exception: {str(e)}")
                print(traceback.format_exc())

            print(f"Request failed, preparing to retry...")

        print(f"Maximum retry count reached, returning empty result")
        return {} if result_key else ""  # Return empty dictionary or empty string as needed

    def format_plot_planning_output(self, planning_data):
        """Format plot planning output (adapt to new data structure), and display dynamic outline and current story progress"""
        output = "### 5. Current Section Plot Planning\n\n"

        # Scene information section
        scene = planning_data["plot_planning"]["scene"]
        output += "#### Scene Setting\n"
        output += f"- **Core Location**: {scene['location']}\n"
        output += f"- **Appearing Characters**: {', '.join(scene['characters'])}\n"
        output += f"- **Scene Tone**: {scene['mood']}\n\n"

        # Current section event description section
        output += "#### Current Section Plot Development\n"
        formatted_action = scene["action"].replace("\n", "\n  ")
        output += f"  {formatted_action}\n\n"

        # Dynamic outline display section
        output += "#### Dynamic Outline\n"
        dynamic_outline = planning_data["plot_planning"].get("dynamic_outline", {})

        # Get event numbers and sort by numerical size
        event_keys = sorted([k for k in dynamic_outline.keys()], key=lambda x: int(x))

        # Display all events
        for key in event_keys:
            output += f"- **Event {key}**: {dynamic_outline[key]}\n"

        # Current story progress
        output += f"\n#### Current Story Progress\nCurrent progress to: Event {planning_data['plot_planning']['current_progress']}\n"

        return output

    def generate_narrative_style(self, max_retries=3):

        # First version of prompt
        system_message = """You are a professional story creation consultant, based on Situation Model Theory, which holds that detailed sensory and situational information helps construct vivid mental representations, thereby enhancing narrative impact. Your task is to provide detailed writing suggestions for the current section event, with the following specific requirements:
        - Clearly indicate which environmental details, character behaviors, dialogues, psychological changes, etc. should be emphasized;
        - Propose at least two suggestions that can increase story detail and innovation;
        - The return format must strictly comply with the following English JSON format:
        {
            "narrative": {
                "focus": ["Focus content 1", "Focus content 2", ...],
                "techniques": ["Innovation technique 1", "Innovation technique 2", ...],
                "tips": ["Improvement suggestion 1", "Improvement suggestion 2", ...]
            }
        }
        Note:
        1. Must strictly return according to the above English JSON format, do not add any other content or comments;
        2. Elements in each array should be complete sentences, specifically describing the suggested content."""

        prompt = f"""Based on the current section event, provide writing suggestions to expand the event in detail:
        Current section event: {self.plot_planning['scene']}

        Please return JSON data strictly according to the following example format:
        {{
            "narrative": {{
                "focus": ["For example: Describe the background environment in detail, specific lighting and prop details", "For example: Depict subtle eye contact and body movements between characters"],
                "techniques": ["For example: Use contrast techniques to highlight tense atmosphere", "For example: Use internal monologues to enhance character emotional expression"],
                "tips": ["For example: Add specific dialogues to reflect authentic character interactions", "For example: Supplement scene detail descriptions to create vivid imagery"]
            }}
        }}"""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                # Clean the returned data
                result = result.strip()
                # Remove possible code block markers
                result = re.sub(r'^```json\s*|\s*```$', '', result)
                # Remove possible excess whitespace characters
                result = re.sub(r'\s+', ' ', result)

                try:
                    narrative_style = json.loads(result)
                    if 'narrative' in narrative_style:
                        narrative = narrative_style['narrative']
                        if all(key in narrative for key in ['focus', 'techniques', 'tips']):
                            # Ensure all fields are lists
                            if isinstance(narrative['focus'], str):
                                narrative['focus'] = [narrative['focus']]
                            if isinstance(narrative['techniques'], str):
                                narrative['techniques'] = [narrative['techniques']]
                            if isinstance(narrative['tips'], str):
                                narrative['tips'] = [narrative['tips']]

                            self.narrative_style = narrative_style
                            return self.format_narrative_style_output(narrative_style)
                        else:
                            print(f"Missing necessary fields, current data: {narrative}")
                            continue
                    else:
                        print("Returned JSON is missing the narrative field")
                        continue
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")
                    print(f"Data attempted to parse: {result}")
                    if attempt == max_retries - 1:
                        return f"Error: Unable to parse returned JSON format. Raw data: {result}"
                    continue

            except Exception as e:
                print(f"Exception occurred: {str(e)}")
                if attempt == max_retries - 1:
                    return f"Error occurred: {str(e)}"
                continue

        return "Unable to get a response in the correct format"

    def format_narrative_style_output(self, narrative_style_data):
        """Format narrative style output"""
        try:
            output = "6. Writing Suggestions:\n\n"
            narrative = narrative_style_data['narrative']

            # Focus content
            output += "## Key Focus Points\n"
            for focus in narrative['focus']:
                output += f"- {focus}\n"
            output += "\n"

            # Innovation techniques
            output += "## Innovation Techniques\n"
            for technique in narrative['techniques']:
                output += f"- {technique}\n"
            output += "\n"

            # Improvement suggestions
            output += "## Improvement Suggestions\n"
            for tip in narrative['tips']:
                output += f"- {tip}\n"

            return output
        except Exception as e:
            print(f"Error occurred when formatting output: {str(e)}")
            return f"Formatting output error: {str(e)}"

    def parse_formatted_background_to_json(self, formatted_background):
        """Convert formatted background setting text back to JSON format"""
        # Initialize JSON structure
        background_json = {
            "world_setting": {
                "time_period": "",
                "environment": "",
                "social_structure": "",
                "recent_changes": []
            },
            "rules_and_systems": {
                "core_rules": "",
                "limitations": "",
                "special_elements": "",
                "rule_changes": []
            }
        }

        # Check if input is empty
        if not formatted_background:
            return background_json

        # First try to extract the entire background setting section
        background_section = formatted_background
        if "Background Setting" in formatted_background:
            bg_match = re.search(r"(?:^|\n)[\d\.\s]*Background Setting:?\s*\n((?:.*\n)*?)(?:\n\n|$)",
                                 formatted_background)
            if bg_match:
                background_section = bg_match.group(1)

        # Extract World View section
        world_content = ""
        world_match = re.search(r"(?:###\s*World View|World View:)((?:.*\n)*?)(?:(?:###|Rules and Settings)|\Z)",
                                background_section,
                                re.DOTALL)
        if world_match:
            world_content = world_match.group(1)

        # Extract Rules and Settings section
        rules_content = ""
        rules_match = re.search(r"(?:###\s*Rules and Settings|Rules and Settings:)((?:.*\n)*?)(?:(?:###)|\Z)",
                                background_section,
                                re.DOTALL)
        if rules_match:
            rules_content = rules_match.group(1)

        # If World View or Rules and Settings sections not found, try broader patterns
        if not world_content:
            world_match = re.search(
                r"Time period:\s*(.*?)(?:\n|$).*?Environment:\s*(.*?)(?:\n|$).*?Social structure:\s*(.*?)(?:\n|$)",
                background_section, re.DOTALL)
            if world_match:
                background_json["world_setting"]["time_period"] = world_match.group(1).strip()
                background_json["world_setting"]["environment"] = world_match.group(2).strip()
                background_json["world_setting"]["social_structure"] = world_match.group(3).strip()
        else:
            # Extract attributes from World View content
            time_match = re.search(r"-\s*Time period:\s*(.*?)(?:\n|$)", world_content)
            if time_match:
                background_json["world_setting"]["time_period"] = time_match.group(1).strip()

            env_match = re.search(r"-\s*Environment:\s*(.*?)(?:\n|$)", world_content)
            if env_match:
                background_json["world_setting"]["environment"] = env_match.group(1).strip()

            social_match = re.search(r"-\s*Social structure:\s*(.*?)(?:\n|$)", world_content)
            if social_match:
                background_json["world_setting"]["social_structure"] = social_match.group(1).strip()

            # Extract recent changes (if any)
            changes_match = re.search(r"-\s*Recent changes:\s*((?:.*\n)*?)(?:-|\Z)", world_content)
            if changes_match:
                changes_content = changes_match.group(1)
                changes = re.findall(r"\*\s*(.*?)(?:\n|$)", changes_content)
                background_json["world_setting"]["recent_changes"] = [change.strip() for change in changes if
                                                                      change.strip()]

        if not rules_content:
            rules_match = re.search(
                r"Core rules:\s*(.*?)(?:\n|$).*?World limitations:\s*(.*?)(?:\n|$).*?Special settings:\s*(.*?)(?:\n|$)",
                background_section, re.DOTALL)
            if rules_match:
                background_json["rules_and_systems"]["core_rules"] = rules_match.group(1).strip()
                background_json["rules_and_systems"]["limitations"] = rules_match.group(2).strip()
                background_json["rules_and_systems"]["special_elements"] = rules_match.group(3).strip()
        else:
            # Extract attributes from Rules and Settings content
            core_match = re.search(r"-\s*Core rules:\s*(.*?)(?:\n|$)", rules_content)
            if core_match:
                background_json["rules_and_systems"]["core_rules"] = core_match.group(1).strip()

            limit_match = re.search(r"-\s*World limitations:\s*(.*?)(?:\n|$)", rules_content)
            if limit_match:
                background_json["rules_and_systems"]["limitations"] = limit_match.group(1).strip()

            special_match = re.search(r"-\s*Special settings:\s*(.*?)(?:\n|$)", rules_content)
            if special_match:
                background_json["rules_and_systems"]["special_elements"] = special_match.group(1).strip()

            # Extract rule changes (if any)
            rule_changes_match = re.search(r"-\s*Rule changes:\s*((?:.*\n)*?)(?:-|\Z)", rules_content)
            if rule_changes_match:
                rule_changes_content = rule_changes_match.group(1)
                rule_changes = re.findall(r"\*\s*(.*?)(?:\n|$)", rule_changes_content)
                background_json["rules_and_systems"]["rule_changes"] = [change.strip() for change in rule_changes if
                                                                        change.strip()]

        return background_json

    def update_background(self, previous_stories, background, max_retries=3):
        """Update the background setting, update the world view and rules based on the previous development"""

        current_background = self.parse_formatted_background_to_json(background)

        system_message = """You are a World Builder, an expert focused on tracking dynamic world changes.
        Based on Cognitive World-Building Theory, you need to identify key events that cause world changes in the story, and ensure these changes align with the world's internal logic.

        Your task is to only analyze newly occurring important changes and rule changes, without modifying or repeating other parts of the original background setting.
        Please only return JSON arrays of these two types of new changes, do not return the complete background setting.
        Remember, if no new changes are detected, clearly mark that there are no new changes."""

        prompt = f"""As a World Builder, please analyze key changes in the following content:

        Previous content:
        {previous_stories}

        Original background setting:
        {json.dumps(current_background, ensure_ascii=False, indent=2)}

        Please carefully analyze the previous content, identifying important events that may cause world changes. These changes must:
        1. Conform to the world's internal consistency, not violating established rules
        2. Be reasonable continuations of story events
        3. Have substantial impact on future story development
        4. Not duplicate changes already recorded in the original background setting

        Please only return the following JSON structure, which contains two fields:
        - has_new_changes: Boolean value indicating whether new changes were detected
        - If has_new_changes is true, provide arrays of new changes

        {{
            "has_new_changes": true/false,
            "recent_changes": ["New important change 1", "New important change 2", ...],  // Only provided when has_new_changes is true
            "rule_changes": ["New rule change 1", "New rule change 2", ...]     // Only provided when has_new_changes is true
        }}

        If no new changes are detected, simply return:
        {{
            "has_new_changes": false
        }}"""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                json_str = result
                if '```json' in result:
                    json_str = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
                    if json_str:
                        json_str = json_str.group(1)
                elif '```' in result:
                    json_str = re.search(r'```\s*(.*?)\s*```', result, re.DOTALL)
                    if json_str:
                        json_str = json_str.group(1)

                json_str = json_str.strip()

                try:
                    changes_data = json.loads(json_str)
                    original_background = current_background

                    if changes_data.get("has_new_changes", False):

                        if 'recent_changes' in changes_data:
                            original_background['world_setting']['recent_changes'] = changes_data['recent_changes']

                        if 'rule_changes' in changes_data:
                            original_background['rules_and_systems']['rule_changes'] = changes_data['rule_changes']

                    self.background = original_background
                    formatted_output = self.format_updated_background_output(original_background)
                    self.writing_guide.update_section('background', formatted_output)
                    return formatted_output

                except json.JSONDecodeError as je:
                    print(f"JSON Parsing Error: {je}")
                    if attempt == max_retries - 1:
                        return "Error: Unable to parse the returned JSON format"
                    continue

            except Exception as e:
                print(f"An error occurred while updating background settings: {e}")
                if attempt == max_retries - 1:
                    return f"An error occurred：{str(e)}"
                    continue

        return "Unable to get a properly formatted response"

    def format_updated_background_output(self, background_data):
        """Format updated background setting output"""
        output = "2. Background Setting:\n\n"

        # World view section
        output += "### World View\n"
        world = background_data['world_setting']
        output += f"- Time period: {world['time_period']}\n"
        output += f"- Environment: {world['environment']}\n"
        output += f"- Social structure: {world['social_structure']}\n"
        output += "- Recent changes:\n"
        for change in world['recent_changes']:
            output += f"  * {change}\n"
        output += "\n"

        # Rules and settings section
        output += "### Rules and Settings\n"
        rules = background_data['rules_and_systems']
        output += f"- Core rules: {rules['core_rules']}\n"
        output += f"- World limitations: {rules['limitations']}\n"
        output += f"- Special settings: {rules['special_elements']}\n"
        output += "- Rule changes:\n"
        for change in rules['rule_changes']:
            output += f"  * {change}\n"

        return output

    def formatted_characters_to_json(self, formatted_text):
        """
        Convert formatted character setting text back to JSON format.
        Can handle both initial character generation and character update formats.

        Args:
            formatted_text (str): Formatted character setting text

        Returns:
            dict: Dictionary with a "characters" key, whose value is a list of character dictionaries
        """
        # Determine if this is initial character generation or character update
        is_update = "Character Settings Update:" in formatted_text

        # Initialize result
        result = {"characters": []}

        # Remove title
        if is_update:
            content = formatted_text.replace("4. Character Settings Update:", "").strip()
        else:
            content = formatted_text.replace("4. Character Settings:", "").strip()

        # Split content into character blocks
        if is_update:
            # For update format, split by separator line or next ## heading
            sections = re.split(r'-{10,}|\n(?=## )', content)
        else:
            # For initial format, split by ## heading
            sections = re.split(r'\n(?=## )', content)

        sections = [s.strip() for s in sections if s.strip()]

        for section in sections:
            # Skip if there's no character title
            if not section.startswith("## "):
                continue

            character = {}
            lines = section.split("\n")

            # Extract name and role type from the first line
            header_match = re.match(r'## (.*?) \((.*?)\)', lines[0])
            if header_match:
                character["name"] = header_match.group(1).strip()
                character["role_type"] = header_match.group(2).strip()
            else:
                continue  # Skip if unable to extract name and role type

            # Process the rest of the block line by line
            current_field = None
            field_content = ""

            for i, line in enumerate(lines[1:], 1):
                # Check survival status in update format
                if is_update and line.startswith("Survival status:"):
                    character["is_alive"] = "Alive" in line
                    continue

                # Check block headings
                if line.startswith("### "):
                    # Save previous field content if exists
                    if current_field and field_content:
                        character[current_field] = field_content.strip()
                        field_content = ""

                    # Set new field based on heading
                    if "Background Introduction" in line:
                        current_field = "background"
                    elif "Background" in line:
                        current_field = "background"
                    elif "Previous Section Character State" in line:
                        current_field = "current_state"
                    else:
                        current_field = None  # Unknown heading

                # Skip empty lines and separator lines
                elif line and not line.startswith("-" * 10):
                    # Add content if current field exists
                    if current_field:
                        field_content += line + "\n"

            # Save the content of the last field
            if current_field and field_content:
                character[current_field] = field_content.strip()

            result["characters"].append(character)

        return result

    def update_characters(self, previous_stories, characters, max_retries=3):
        """Update character settings, including development status of existing characters and addition of new characters"""

        system_message = """You are a Character Designer - an expert responsible for the rationality of character motivation and development.
        You create based on Character Arc Theory, with particular attention to how characters evolve throughout the story:
        1. Gradual change - Character changes should conform to the natural laws of psychological development, avoiding abrupt transformations
        2. Motivation consistency - Even if character behaviors change, they should stem from the continuation of their core motivations
        3. Growth markers - Display characters' internal changes through specific actions, decisions, and emotional responses
        4. Transformation catalysts - Identify key events or relationships in the story that trigger character transformations
        5. Consequences and adaptation - How characters respond to the results brought by changes, and adjustments to self-perception

        Please update character settings based on the previous content, with focus on:
        1. Each character's specific performance and psychological changes in the previous section of the story
        2. Update existing characters' current_state and is_alive status
        3. If new characters appear in the previous content, add the newly appeared characters
        4. Mark characters' survival status
        Please output analysis results strictly in English JSON format."""

        prompt = f"""As a character psychologist, please analyze and update characters' psychological development trajectories based on the following information:

        Previous content:
        {previous_stories}

        Existing character settings:
        {self.formatted_characters_to_json(characters)}

        Please carefully analyze each character's words and actions, decision-making processes, and emotional responses in the previous content, focusing on:
        1. What core traits are revealed by how characters respond to challenges
        2. How interactions with other characters affect their psychological state
        3. What key events characters have experienced that might lead to internal transformations
        4. How characters' current psychological states differ from their initial states

        Please return updated character settings in the following English JSON format:

        {{
            "characters": [
                {{
                    "name": "Character name",
                    "role_type": "Character type (such as protagonist/antagonist/supporting character, etc.)",
                    "is_alive": true/false,
                    "background": "A brief introduction to the character's background (about 50 words)",
                    "current_state": "Scene-based description of the character's specific actions, experiences, and psychological changes in the previous section of the story, highlighting the character's current situation and emotions (about 50 words)"
                }}
            ]
        }}

        Note:
        1. For each character, you must provide current_state
        2. current_state should specifically describe the character's performance and internal psychological changes in the previous section of the story
        3. If new characters appear, please add complete character information
        4. No other information should be modified"""

        for attempt in range(max_retries):
            try:
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]

                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=messages
                )

                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                json_str = result
                if '```json' in result:
                    json_str = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
                    if json_str:
                        json_str = json_str.group(1)
                elif '```' in result:
                    json_str = re.search(r'```\s*(.*?)\s*```', result, re.DOTALL)
                    if json_str:
                        json_str = json_str.group(1)

                json_str = json_str.strip()

                try:
                    updated_characters = json.loads(json_str)
                    if 'characters' in updated_characters:

                        for char in updated_characters['characters']:
                            if 'current_state' not in char or not char['current_state']:
                                raise ValueError(f"character {char['name']} lack current_state")

                        self.characters = updated_characters
                        formatted_output = self.format_updated_characters_output(updated_characters)
                        self.writing_guide.update_section('characters', formatted_output)
                        return formatted_output
                except json.JSONDecodeError as je:
                    print(f"JSON parsing error: {je}")
                    if attempt == max_retries - 1:
                        return "Error: Unable to parse the returned JSON format"
                    continue

            except Exception as e:
                print(f"An error occurred while updating character settings: {e}")
                if attempt == max_retries - 1:
                    return f"An error occurred：{str(e)}"
                continue

        return "Unable to get a properly formatted response"

    def format_updated_characters_output(self, characters_data):
        """Format updated character settings output"""
        output = "4. Character Settings Update:\n"

        for char in characters_data['characters']:
            output += f"\n## {char['name']} ({char['role_type']})\n"
            output += f"Survival status: {'Alive' if char['is_alive'] else 'Dead'}\n\n"

            # Character background
            output += "### Background Introduction\n"
            output += f"{char['background']}\n\n"

            # Current state
            output += "### Previous Section Character State\n"
            output += f"{char['current_state']}\n"

            output += "\n" + "-" * 50 + "\n"  # Separator line

        return output

    def _parse_plot_planning(self, formatted_text):
        """Convert formatted plot planning text to JSON structure"""

        def extract_block(header, text):
            """
            Extract content from specified header to the next header or end of text
            """
            pattern = rf'####\s*{header}\s*\n(.*?)(?=\n####|\Z)'
            m = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            return m.group(1).strip() if m else ""

        try:
            # Scene Setting section
            scene_text = extract_block("Scene Setting", formatted_text)
            location_match = re.search(r'-\s*\*\*Core Location\*\*:\s*(.*)', scene_text)
            location = location_match.group(1).strip() if location_match else ""
            characters_match = re.search(r'-\s*\*\*Appearing Characters\*\*:\s*(.*)', scene_text)
            characters = [x.strip() for x in characters_match.group(1).split(',')] if characters_match else []
            mood_match = re.search(r'-\s*\*\*Scene Tone\*\*:\s*(.*)', scene_text)
            mood = mood_match.group(1).strip() if mood_match else ""

            # Current Section Plot Development section
            action_text = extract_block("Current Section Plot Development", formatted_text)

            # Dynamic Outline section
            dynamic_outline_block = extract_block("Dynamic Outline", formatted_text)
            dynamic_outline = {}
            if dynamic_outline_block:
                for line in dynamic_outline_block.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r'-\s*\*\*Event\s*(\d+)\*\*:\s*(.*)', line)
                    if m:
                        key = m.group(1).strip()
                        dynamic_outline[key] = m.group(2).strip()

            # Current Story Progress section: match both with and without title, and both "to:" and "at:"
            m_progress = re.search(
                r'(?:####\s*Current Story Progress\s*\n)?\s*Current progress (?:to|at):\s*Event\s*(\d+)',
                formatted_text, re.DOTALL | re.MULTILINE)
            current_progress = m_progress.group(1).strip() if m_progress else "1"

            return {
                "plot_planning": {
                    "scene": {
                        "location": location,
                        "characters": characters,
                        "mood": mood,
                        "action": action_text
                    },
                    "dynamic_outline": dynamic_outline,
                    "current_progress": current_progress
                }
            }
        except Exception as e:
            print(f"[ERROR] Failed to parse plot planning: {str(e)}")
            return None

    def update_plot_planning(self, previous_stories, genre_style, background, characters, core_plot,
                             plot_planning, max_retries=3):
        """
        Update plot planning:
        According to the progress of the dynamic outline in the previous plot planning, automatically select the next section in the dynamic outline to generate the current plot planning,
        and add details to subsequent events based on the story content of the previous section to ensure the continuity and richness of the story.
        """

        previous_parsed = self._parse_plot_planning(plot_planning)['plot_planning']
        print(f"update_plot_planning的测试，Previous parsed: {previous_parsed}")

        print(f"Previous sectionCurrent event index: {previous_parsed['current_progress']}")

        dynamic_outline = previous_parsed.get('dynamic_outline', {})
        current_progress = previous_parsed.get('current_progress', "0")

        current_progress_int = int(current_progress) if str(current_progress).isdigit() else 0

        if dynamic_outline:
            max_event = max(int(k) for k in dynamic_outline.keys() if k.isdigit())
        else:
            max_event = 0
            print("Warning: No valid dynamic outline found")

        if current_progress_int < max_event:
            event_key = str(current_progress_int + 1)
        else:
            event_key = str(max_event)
            print(f"The end of the dynamic outline has been reached (event {max_event})")

        print(f"The current event index is {event_key}, and the total number of events is {max_event}")

        if previous_stories:
            dynamic_outline = self._update_dynamic_outline(
                dynamic_outline,
                event_key,
                previous_stories,
                max_retries
            )

        event_description = dynamic_outline.get(event_key, "no description")

        scene_info = self._extract_scene_elements(event_description, max_retries)

        scene_info["action"] = event_description

        final_planning = {
            "plot_planning": {
                "scene": scene_info,
                "dynamic_outline": dynamic_outline,
                "current_progress": event_key
            }
        }

        self.plot_planning = final_planning.get("plot_planning", {})
        return self.format_update_plot_planning_output(final_planning)

    def _update_dynamic_outline(self, current_outline, current_key, previous_content, max_retries=3):
        """
        Update the subsequent events in the dynamic outline according to the story content of the previous section, add details and precise descriptions

        Args:
        current_outline: current dynamic outline
        current_key: key of the current event
        previous_content: story content of the previous section
        max_retries: maximum number of retries

        Returns:
        Updated dynamic outline
        """

        current_and_future_events = {
            k: v for k, v in current_outline.items()
            if k.isdigit() and int(k) >= int(current_key)
        }

        previous_events = {
            k: v for k, v in current_outline.items()
            if k.isdigit() and int(k) < int(current_key)
        }

        if not current_and_future_events:
            print("There are no more events to update, keep the original outline unchanged")
            return current_outline

        # Get the exact event keys from the original outline for strict validation
        original_event_keys = [k for k in current_outline.keys() if k.isdigit()]
        original_event_count = len(original_event_keys)
        original_event_keys_set = set(original_event_keys)

        # Create system message
        system_message = (
            "You are a novelist skilled in story planning, focused on making story plots concrete, objective, and coherent. "
            "Your task is to make subtle adjustments to current and future events based on the previous section's content and existing dynamic outline, "
            "mainly by adding specific details (such as location names, event names, character traits, etc.) to enrich event descriptions, while maintaining an objective narrative style. "
            f"IMPORTANT: You MUST maintain EXACTLY {original_event_count} events with the EXACT SAME event numbers. DO NOT add any new events or remove any existing events. "
            "Each event description must objectively state facts, without using any rhetorical techniques (such as metaphors, personification, etc.), without including dialogue, "
            "and without any meta-narrative about 'story stages', 'next stage', or 'trigger events'. "
            "Remember, the dynamic outline is the framework of the story and needs to be objective and precise, while rhetorical techniques should be left for the story text."
        )

        # Create events list string
        events_str = ""
        for k, v in sorted(current_and_future_events.items(), key=lambda x: int(x[0])):
            events_str += f"Event {k}: {v}\n"

        prompt = f"""Based on the previous section's content and existing dynamic outline, please make subtle adjustments to the current event (Event {current_key}) and subsequent events, mainly by adding specific details to improve the precision of event descriptions.

            Requirements:
            - CRITICAL: You MUST maintain EXACTLY {original_event_count} events total in the outline
            - CRITICAL: Use ONLY these exact event numbers: {", ".join(sorted(original_event_keys, key=int))}
            - DO NOT add any new event numbers or remove any existing ones
            - DO NOT change the core content and basic direction of events
            - Enrich event descriptions by adding specific details, such as specific location names, event names, character identities, precise times, etc.
            - Based on the previous section's content, ensure logical coherence between events
            - Event descriptions must be objective factual statements, without using any rhetorical techniques
            - Do not include any dialogue, character inner thoughts, or metaphorical descriptions
            - Do not mention meta-narrative elements like "next stage", "trigger event", "story stage" in event descriptions

            Previous section content:
            {previous_content}

            Current and subsequent events that need adjustment:
            {events_str}

            Please output the updated event descriptions in JSON format, including ONLY the original event numbers that need updating:
            {{
              "updated_outline": {{
                "{list(current_and_future_events.keys())[0]}": "Updated event description",
                ...
              }}
            }}
            """

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                cleaned_result = re.sub(r'```(json)?|```', '', result, flags=re.DOTALL).strip()
                json_match = re.search(r'\{[\s\S]*\}', cleaned_result, flags=re.DOTALL)
                if not json_match:
                    raise ValueError("No valid JSON format output detected")

                json_str = json_match.group().strip()
                data = json.loads(json_str)

                if "updated_outline" not in data:
                    raise ValueError("The returned JSON does not contain the 'updated_outline' key")

                updated_outline = data["updated_outline"]

                # Strict validation: Check if there are any new event keys not in original outline
                updated_keys = [k for k in updated_outline.keys() if k.isdigit()]
                updated_keys_set = set(updated_keys)
                extra_keys = updated_keys_set - original_event_keys_set

                if extra_keys:
                    print(f"Error: Found extra event keys not in original outline: {extra_keys}")
                    raise ValueError(f"Updated outline contains extra events: {extra_keys}")

                # Check for missing keys
                missing_keys = []
                for key in current_and_future_events.keys():
                    if key not in updated_outline:
                        missing_keys.append(key)

                if missing_keys:
                    print(f"Warning: Updates returned are missing the following event keys: {', '.join(missing_keys)}")
                    for key in missing_keys:
                        updated_outline[key] = current_and_future_events[key]

                # Merge previous events with updated events
                merged_outline = {**previous_events, **updated_outline}

                # Final validation to ensure outline integrity
                merged_keys = [k for k in merged_outline.keys() if k.isdigit()]
                if len(merged_keys) != original_event_count:
                    print(f"Error: Final outline contains {len(merged_keys)} events, expected {original_event_count}")
                    raise ValueError(f"Event count mismatch: Got {len(merged_keys)}, expected {original_event_count}")

                if set(merged_keys) != original_event_keys_set:
                    missing_final = original_event_keys_set - set(merged_keys)
                    extra_final = set(merged_keys) - original_event_keys_set
                    error_msg = "Event keys mismatch. "
                    if missing_final:
                        error_msg += f"Missing: {missing_final}. "
                    if extra_final:
                        error_msg += f"Extra: {extra_final}."
                    raise ValueError(error_msg)

                # Preserve any non-numeric keys in the original outline
                for key in current_outline:
                    if not key.isdigit() and key not in merged_outline:
                        merged_outline[key] = current_outline[key]

                print(f"Successfully updated dynamic outline, updated {len(updated_outline)} events")
                return merged_outline

            except Exception as e:
                print(f"Update dynamic outline. Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"Failed to update the dynamic outline, keeping the original outline unchanged")
                    return current_outline

        return current_outline

    def _extract_scene_elements(self, event_description, max_retries=3):
        """
        Extract scene elements (location, characters, emotional tone) from the event description

        Args:
            event_description: Event description
            max_retries: Maximum number of retries

        Returns:
            Dictionary containing scene elements
        """
        system_message = (
            "You are an expert in precise scene element extraction. Your task is to analyze the current section's dynamic outline event, "
            "and extract three core elements from it: scene location, appearing characters, and emotional tone. "
            "You must strictly work within the scope of the current event description, and not create or introduce information not explicitly mentioned in the event."
        )

        prompt = f"""Please analyze the following dynamic outline event for the current section, and extract key scene elements:

        Current dynamic outline event:
        {event_description}

        === Analysis Requirements (must be strictly followed) ===
        1. Carefully read the dynamic outline event description, only identify what is explicitly mentioned:
           - Specific locations (exact location where the event takes place)
           - Appearing characters (characters explicitly mentioned in the event)
           - Emotional tone (atmosphere and emotional color of the event)

        2. Strictly follow these principles:
           - Only list characters explicitly mentioned in the event description, do not add any additional characters
           - Scene location must precisely correspond to the location described in the event
           - Emotional tone should be directly derived from the language and content of the event description

        === Output Format ===
        Please output these three elements in strict English JSON format:
        {{
            "location": "Specific location described in the event",
            "characters": ["Character 1 mentioned in the event", "Character 2 mentioned in the event",...],
            "mood": "Emotional tone implied by the event description"
        }}
        """

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, result)

                try:
                    scene_info = json.loads(result)
                except json.JSONDecodeError:

                    json_match = re.search(r'\{[\s\S]*\}', result)
                    if not json_match:
                        raise ValueError("No valid JSON format output detected")
                    json_str = re.sub(r'```json|```', '', json_match.group()).strip()
                    scene_info = json.loads(json_str)

                required_fields = ["location", "characters", "mood"]
                for field in required_fields:
                    if field not in scene_info:
                        raise ValueError(f"The '{field}' field is missing in the returned JSON")

                if not isinstance(scene_info["characters"], list):
                    scene_info["characters"] = [scene_info["characters"]]

                return scene_info

            except Exception as e:
                print(f"Extract scene element. Attempts {attempt + 1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:
                    return {
                        "location": "unknown place",
                        "characters": ["unknown characters"],
                        "mood": "unknown mood"
                    }

        return {
            "location": "unknown place",
            "characters": ["unknown characters"],
            "mood": "unknown mood"
        }

    def format_update_plot_planning_output(self, planning_data):
        """Format plot planning output, and display dynamic outline and current story progress"""
        output = "### 5. Current Section Plot Planning\n\n"

        # Scene information section
        scene = planning_data["plot_planning"]["scene"]
        output += "#### Scene Setting\n"
        output += f"- **Core Location**: {scene['location']}\n"
        output += f"- **Appearing Characters**: {', '.join(scene['characters'])}\n"
        output += f"- **Scene Tone**: {scene['mood']}\n\n"

        # Current section event description part
        output += "#### Current Section Plot Development\n"
        formatted_action = scene["action"].replace("\n", "\n  ")
        output += f"  {formatted_action}\n\n"

        # Dynamic outline display section
        output += "#### Dynamic Outline\n"
        dynamic_outline = planning_data["plot_planning"].get("dynamic_outline", {})

        # Get event numbers and sort them numerically
        event_keys = sorted([k for k in dynamic_outline.keys()], key=lambda x: int(x))

        # Display all events
        for key in event_keys:
            output += f"- **Event {key}**: {dynamic_outline[key]}\n"

        # Current story progress
        output += f"\n#### Current Story Progress\nCurrent progress at: Event {planning_data['plot_planning']['current_progress']}\n"

        return output

    def update_narrative_style(self, plot_planning, max_retries=3):
        """Update narrative style suggestions, provide independent writing advice based on current section events"""

        # Second version of prompt
        system_message = """You are a professional story creation consultant, based on Situation Model Theory, which emphasizes helping readers build vivid mental representations through detailed environmental and situational descriptions, thereby enhancing the expressiveness of the story. Your task is to provide detailed writing suggestions for the current section's events, with specific requirements as follows:
        - Clearly indicate which environmental details, character behaviors, dialogues, psychological changes, etc. should be emphasized;
        - Propose at least two suggestions that can increase story detail and innovation;
        - The return format must strictly comply with the following English JSON format:
        {
            "narrative": {
                "focus": ["Focus content 1", "Focus content 2", ...],
                "techniques": ["Innovative technique 1", "Innovative technique 2", ...],
                "tips": ["Improvement suggestion 1", "Improvement suggestion 2", ...]
            }
        }
        Note:
        1. Must strictly return according to the above English JSON format, do not add any other content or comments;
        2. Each element in the arrays should be a complete sentence, specifically describing the suggested content."""

        prompt = f"""Please provide writing suggestions based on the current section's events to expand the events in detail:
        Current section event: {self.extract_plot_planning(plot_planning)['plot_planning']['scene']['action']}

        Please return JSON data strictly according to the following example format:
        {{
            "narrative": {{
                "focus": ["For example: Describe the environmental atmosphere in detail, specific lighting and prop details", "For example: Portray subtle eye contact and body language between characters"],
                "techniques": ["For example: Use contrast techniques to highlight tense atmosphere", "For example: Use internal monologues to enhance character emotional expression"],
                "tips": ["For example: Add specific dialogues to reflect authentic character interactions", "For example: Supplement scene detail descriptions to create vivid imagery"]
            }}
        }}"""

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )
                raw_content = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_content)


                cleaned_content = re.sub(r'^```json\s*|```$', '', raw_content).strip()
                updated_style = json.loads(cleaned_content)

                if all(key in updated_style.get('narrative', {}) for key in ['focus', 'techniques', 'tips']):
                    self.narrative_style = updated_style
                    formatted_output = self._format_updated_narrative_output(updated_style)
                    self.writing_guide.update_section('narrative_style', formatted_output)
                    return formatted_output
                raise ValueError("The returned data structure is incomplete")

            except (json.JSONDecodeError, KeyError) as e:
                print(f"JSON parsing failed (try {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    return "Error: Unable to obtain valid update suggestions"
            except Exception as e:
                print(f"Update failed：{str(e)}")
                if attempt == max_retries - 1:
                    return f"Final failure：{str(e)}"

        return "Update attempts exhausted"

    def _format_updated_narrative_output(self, style_data):
        """Format updated narrative style output"""
        output = "6. Writing Suggestions Update:\n\n"
        narrative = style_data['narrative']

        output += "## Latest Focus Directions\n"
        for idx, item in enumerate(narrative['focus'], 1):
            output += f"{idx}. {item}\n"

        output += "\n## Applicable Innovative Techniques\n"
        for idx, item in enumerate(narrative['techniques'], 1):
            output += f"{idx}. {item}\n"

        output += "\n## Targeted Improvement Suggestions\n"
        for idx, item in enumerate(narrative['tips'], 1):
            output += f"{idx}. {item}\n"

        return output

    def check_story_completion(self, writing_guide):
        """
        Determine whether the story is complete based on the number of dynamic outline events:
        When the current event number reaches the maximum event number in the dynamic outline, the story is considered complete.
        """

        try:

            plot_data = self.extract_plot_planning(writing_guide.get("plot_planning", ""))

            current_progress = plot_data.get("plot_planning", {}).get("current_progress", "0")
            dynamic_outline = plot_data.get("plot_planning", {}).get("dynamic_outline", {})

            current_progress_int = int(current_progress) if str(current_progress).isdigit() else 0

            max_event = 0
            if dynamic_outline:
                max_event = max(int(k) for k in dynamic_outline.keys() if k.isdigit())

            is_completed = max_event > 0 and current_progress_int >= max_event

            reason = ""
            if is_completed:
                reason = f"The story has reached the maximum event in the dynamic outline (section {max_event}) and has ended naturally."
            else:
                reason = f"The story is not finished yet. The current progress is the {current_progress_int}th section. The dynamic outline has a total of {max_event} sections."

            result = {
                "is_completed": is_completed,
                "reason": reason
            }

            print(f"check_story_completion result: {result}")
            return result

        except Exception as e:
            error_result = {"is_completed": False,
                            "reason": f"An error occurred while checking the story completion status：{str(e)}"}
            print(f"check_story_completion error: {error_result}")
            return error_result


class WritingGuide:
    def __init__(self):
        self.story_summary = ""  # 添加这一行
        self.genre_style = ""
        self.background = ""
        self.characters = ""
        self.core_plot = ""
        self.plot_planning = ""
        self.narrative_style = ""
        self.complete_guide = ""

    def set_complete_guide(self, guide_content):
        """Directly set up the complete writing guide content"""
        self.complete_guide = guide_content

    def generate_story_summary(self, client, previous_stories):
        """Generate a background summary"""
        if not previous_stories:
            return None

        system_message = """You are a professional novel editor.
        Your task is to summarize the content of previous chapters, generating a concise but complete recap.
        You must strictly return content in the specified English JSON format, without adding any other explanations, dialogues, or descriptions."""

        prompt = f"""Please read the following previous content and generate a clear recap:

        Previous content:
        {previous_stories}

        Requirements:
        1. Keep the summary within 100 words
        2. Outline important events in chronological order
        3. Highlight key points that influence subsequent plot developments
        4. Use concise and clear language
        5. Do not include comments or subjective judgments

        Must strictly return in the following English JSON format, without adding any other content:
        {{
            "summary": "Your recap content"
        }}"""

        try:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]

            response = client.chat.completions.create(
                model="glm-4-air",
                messages=messages
            )

            result = response.choices[0].message.content.strip()


            # Process JSON response
            try:
                # Clean possible markdown code block markers
                import re
                import json

                cleaned_result = re.sub(r'^```(json)?|```$', '', result, flags=re.MULTILINE).strip()

                # Try to match JSON part
                json_match = re.search(r'(\{[\s\S]*\})', cleaned_result)

                if json_match:
                    json_str = json_match.group(1)
                    data = json.loads(json_str)

                    if "summary" in data:
                        summary = data["summary"].strip()

                        # Check if title is already included
                        if not summary.startswith("## Recap"):
                            formatted_summary = "## Recap\n\n" + summary
                        else:
                            formatted_summary = summary

                        # Update recap
                        self.story_summary = formatted_summary
                        self._update_complete_guide()

                        return formatted_summary
                    else:
                        print("'summary' field missing in returned JSON")
                else:
                    print("Failed to extract valid JSON format from response")

                # If JSON parsing fails, try to use the returned text directly
                if result:
                    if not result.startswith("## Recap"):
                        formatted_summary = "## Recap\n\n" + result
                    else:
                        formatted_summary = result

                    # Update recap
                    self.story_summary = formatted_summary
                    self._update_complete_guide()

                    return formatted_summary

            except Exception as e:
                print(f"Error occurred while parsing JSON response: {str(e)}")
                # Try to use the returned text directly as a fallback
                if result:
                    if not result.startswith("## Recap"):
                        formatted_summary = "## Recap\n\n" + result
                    else:
                        formatted_summary = result

                    # Update recap
                    self.story_summary = formatted_summary
                    self._update_complete_guide()

                    return formatted_summary

        except Exception as e:
            print(f"Error occurred while generating recap: {str(e)}")
            return None

    def update_section(self, section_name, content):
        setattr(self, section_name, content)
        self._update_complete_guide()

    def _update_complete_guide(self):
        """Updated Complete Writing Guide"""
        sections = []

        if self.story_summary:
            sections.append(self.story_summary)

        if self.genre_style:
            sections.append(self.genre_style)
        if self.background:
            sections.append(self.background)
        if self.characters:
            sections.append(self.characters)
        if self.core_plot:
            sections.append(self.core_plot)
        if self.plot_planning:
            sections.append(self.plot_planning)
        if self.narrative_style:
            sections.append(self.narrative_style)

        self.complete_guide = "# Writing Guide\n\n" + "\n\n".join(filter(None, sections))

    def get_complete_guide(self):
        return self.complete_guide


class StructureEditor:

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    @staticmethod
    def filter_writing_guidelines(text):
        """
        Filter writing guide content, removing the "3. Core Plot Planning" section and
        "### 5. Current Section Plot Planning" section.
        Deletion range starts from the specified title and continues until the next title
        (e.g., starting with a number or special identifier) is encountered.

        Parameters:
            text (str): Original writing guide text

        Returns:
            str: Filtered writing guide text
        """
        # Remove "3. Core Plot Planning" section:
        filtered = re.sub(
            r"(?ms)^3\.\s*Core Plot Planning[:]?.*?(?=^(?:###\s*5\.|\d+\.)\s*)",
            "",
            text
        )
        # Remove "### 5. Current Section Plot Planning" section:
        filtered = re.sub(
            r"(?ms)^###\s*5\.\s*Current Section Plot Planning[:]?.*?(?=^\d+\.\s*)",
            "",
            filtered
        )
        # Clean up extra blank lines
        filtered = re.sub(r'\n\s*\n', '\n\n', filtered).strip()
        return filtered

    def extract_plot_planning(self, writing_guide):
        """
        Extract plot planning content from the writing guide, supporting dictionary input format

        Args:
            writing_guide: Can be a dictionary (containing plot_planning key) or a string

        Returns:
            Dictionary containing formatted plot planning
        """
        # Initialize default return result
        result = {
            "plot_planning": {
                "scene": {
                    "location": "",
                    "characters": [],
                    "mood": "",
                    "action": ""
                },
                "dynamic_outline": {},
                "current_progress": ""
            }
        }

        try:
            # If it's a dictionary type, extract the plot_planning field
            plot_planning_text = ""
            if isinstance(writing_guide, dict):
                if "plot_planning" in writing_guide:
                    plot_planning_text = writing_guide["plot_planning"]
                else:
                    print("plot_planning field not found in dictionary")
                    return result
            else:
                # If it's a string type, use it directly
                plot_planning_text = writing_guide

            # Ensure plot_planning_text is a string
            if not isinstance(plot_planning_text, str):
                return result

            # Extract scene setting
            scene_pattern = r'####\s*Scene Setting\s*([\s\S]*?)(?=####|\Z)'
            scene_match = re.search(scene_pattern, plot_planning_text)
            if scene_match:
                scene_text = scene_match.group(1).strip()

                # Extract core location
                location_pattern = r'\*\*Core Location\*\*:\s*(.*?)(?=\n|\r|$)'
                location_match = re.search(location_pattern, scene_text)
                if location_match:
                    result["plot_planning"]["scene"]["location"] = location_match.group(1).strip()

                # Extract appearing characters
                characters_pattern = r'\*\*Appearing Characters\*\*:\s*(.*?)(?=\n|\r|$)'
                characters_match = re.search(characters_pattern, scene_text)
                if characters_match:
                    characters_text = characters_match.group(1).strip()
                    result["plot_planning"]["scene"]["characters"] = [c.strip() for c in characters_text.split(',')]

                # Extract scene tone/mood
                mood_pattern = r'\*\*Scene Tone\*\*:\s*(.*?)(?=\n|\r|$)'
                mood_match = re.search(mood_pattern, scene_text)
                if mood_match:
                    result["plot_planning"]["scene"]["mood"] = mood_match.group(1).strip()

            # Extract current section plot development
            action_pattern = r'####\s*Current Section Plot Development\s*([\s\S]*?)(?=####|\Z)'
            action_match = re.search(action_pattern, plot_planning_text)
            if action_match:
                result["plot_planning"]["scene"]["action"] = action_match.group(1).strip()

            # Extract dynamic outline
            outline_pattern = r'####\s*Dynamic Outline\s*([\s\S]*?)(?=####|\Z)'
            outline_match = re.search(outline_pattern, plot_planning_text)
            if outline_match:
                outline_text = outline_match.group(1).strip()

                # Use regular expressions to extract all events
                event_pattern = r'\*\*Event\s*(\d+)\*\*:\s*([\s\S]*?)(?=\*\*Event|\Z)'
                event_matches = re.finditer(event_pattern, outline_text)

                dynamic_outline = {}
                for match in event_matches:
                    event_num = match.group(1).strip()
                    event_text = match.group(2).strip()
                    dynamic_outline[event_num] = event_text

                result["plot_planning"]["dynamic_outline"] = dynamic_outline

            # Extract current story progress
            progress_pattern = r'####\s*Current Story Progress\s*([\s\S]*?)(?=####|\Z)'
            progress_match = re.search(progress_pattern, plot_planning_text)
            if progress_match:
                progress_text = progress_match.group(1).strip()
                # Modificación importante: cambiar el patrón para que capture tanto "to" como "at"
                progress_num_pattern = r'Current progress (?:to|at): Event\s*(\d+)'
                progress_num_match = re.search(progress_num_pattern, progress_text)
                if progress_num_match:
                    result["plot_planning"]["current_progress"] = progress_num_match.group(1).strip()

            return result

        except Exception as e:
            import traceback
            print(f"Failed to parse plot planning: {str(e)}")
            print(traceback.format_exc())
            return result

    def check_story(self, story, guide_dict, max_retries=3):
        writing_guide = guide_dict.get('content', '')

        system_message = """You are a Structure Editor - an expert focusing on plot logic and coherence.
        You analyze based on Robert McKee's story structure theory, systematically explained in his work 'Story: Substance, Structure, Style, and the Principles of Screenwriting', focusing on how to build effective narrative structures:
        1. Value Shift Theory - Each scene should demonstrate positive or negative changes in character status
        2. Plot Progression Principle - The story must advance through conflicts and challenges in the current scene
        3. Crisis-Choice-Climax Pattern - Key scenes should follow this classic structure
        4. Expectation Subversion Principle - Plot twists should be both unexpected and reasonable, but must originate from established elements
        5. Controlling Idea - Each scene needs to revolve around the core purpose planned for the current section

        McKee particularly emphasizes the importance of "Scene Follows Planning" - each scene must faithfully execute its preset structure and function. Scenes that deviate from the preset plan weaken the coherence of the overall narrative. The effectiveness of a scene depends on how accurately it fulfills its specific role in the overall story architecture.

        Please strictly return JSON in the following format, without adding any extra text, comments, or code blocks:
        {
            "suggestions": "specific suggestions"
        }

        Very important:
        1. You must only return a JSON object in the above format, without any other text
        2. Do not add any descriptions, explanations, or code block markers (like ```) before or after the JSON
        3. Your response must be directly parsable by json.loads() without additional processing steps"""

        prompt = f"""As a Structure Editor, please strictly evaluate the structural integrity of the current section based on McKee's story structure theory against the following writing guidelines:

        Current section event planning (analysis should focus on this part): {self.extract_plot_planning(writing_guide)['plot_planning']['scene']}

        Story content:
        {story}

        Please conduct an in-depth analysis from the following aspects, with special focus on the execution of the current section:
        1. Value Shift - Whether the current section strictly demonstrates the expected changes in character status according to the plan
        2. Plot Execution - Whether the current section faithfully implements the conflicts and events specified in the current section event planning, avoiding deviation from the event planning content
        3. Story Consistency - Whether the current section content maintains precise consistency with the planned scenes, characters, and actions
        4. Structural Precision - Whether the current section plot development follows the event process set in the planning, without missing key elements
        5. Causal Logic - Whether the current section events are established within the planned framework, maintaining clear internal logical relationships

        Based on McKee's "Scene Follows Planning" principle, evaluate whether the story precisely executes the preset plan for the current section, avoiding introducing unplanned elements or prematurely showing content from subsequent plots.

        Must return results in pure English JSON format, without adding any other text, comments, or code block markers, directly return:
        {{
        "suggestions": "Detailed specific structural modification suggestions, focusing on how to make the current section more precisely execute its preset planning, pointing out any problems that deviate from the current section planning and how to correct them"
        }}

        Note: The returned JSON must be correctly formatted, without any escape errors or control characters, to ensure it can be parsed by a standard JSON parser."""

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt}]
                )

                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)



                print(f"Story structure check result (attempt {retry_count + 1}/{max_retries}): {raw_result}")

                # Clean JSON string - remove code block markers and control characters
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove all control characters that might cause JSON parsing to fail
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in ['\n', '\r', '\t'])

                # Try to extract JSON object (if result doesn't start with {)
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        # If no JSON object is found, continue to the next retry
                        print(f"No valid JSON object found, will retry...")
                        continue

                try:
                    result = json.loads(json_str)
                    if "suggestions" in result:
                        # Successfully found valid result, return
                        return result
                    else:
                        # JSON parsing successful but missing required field, continue retry
                        print(f"Missing suggestions field in JSON, will retry...")
                        continue
                except json.JSONDecodeError as e:
                    # JSON parsing failed, continue retry
                    print(f"JSON parsing failed: {str(e)}, will retry...")
                    continue

            except Exception as e:
                print(f"API call or processing error: {str(e)}, will retry...")
                # Continue to next retry

        # After all retries fail, return default value
        print("All retries failed, returning default suggestion")
        return {
            "suggestions": "Unable to obtain valid story structure analysis. Please check the story content and try again."}


class EmotionalOrchestrator:

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    def check_story(self, story, max_retries=3):
        system_message = """You are an Emotional Orchestrator - an expert focused on regulating the emotional rhythm of stories and reader experience.
        You analyze based on Reader Response Theory, focusing on how readers interact with text and produce emotional responses:
        1. Interaction Theory - Reading is an interactive process between reader and text, with emotional meaning emerging from this process
        2. Aesthetic vs Informational Reading - Distinguishing between reading modes for emotional experience and information acquisition
        3. Horizon of Expectations - How readers' cultural backgrounds and expectations influence emotional responses
        4. Textual Gaps - How ambiguous areas in the text stimulate readers' emotional imagination
        5. Emotional Arc - Stories should construct a rhythmic curve of emotional fluctuations

        Please strictly return JSON in the following format, without adding any extra text, comments, or code blocks:
        {
            "suggestions": "specific improvement suggestions"
        }

        Very important:
        1. You must only return a JSON object in the above format, without any other text
        2. Do not add any descriptions, explanations, or code block markers (like ```) before or after the JSON
        3. Your response must be directly parsable by json.loads() without additional processing steps"""

        prompt = f"""As an Emotional Orchestrator, please analyze the emotional effects of the following story content based on Reader Response Theory:
        {story}

        Please evaluate from the following aspects:
        1. Emotional Resonance - Whether the story establishes character situations and conflicts that elicit readers' emotional investment
        2. Emotional Rhythm - Whether the story constructs an effective emotional fluctuation curve, avoiding emotional monotony or excessive fluctuations
        3. Aesthetic Engagement - Whether the descriptions are vivid and detailed enough to stimulate readers' sensory and emotional imagination
        4. Textual Gaps - Whether appropriate space is left for readers' emotional participation, rather than over-explaining everything
        5. Emotional Climax - Whether key emotional points are adequately built up and effectively executed

        Please analyze in detail the strengths and weaknesses of each emotional dimension, and provide specific improvement suggestions, with special focus on how to enhance the reader's emotional experience.

        Must return results in pure English JSON format, without adding any other text, comments, or code block markers, directly return:
        {{
        "suggestions": "Specific emotional improvement suggestions based on Reader Response Theory"
        }}

        Note: The returned JSON must be correctly formatted, without any escape errors or control characters, to ensure it can be parsed by a standard JSON parser."""

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)

                print(f"Emotional response result (attempt {retry_count + 1}/{max_retries}): {raw_result}")

                # Clean JSON string - remove code block markers and control characters
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove all control characters that might cause JSON parsing to fail
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in ['\n', '\r', '\t'])

                # Try to extract JSON object (if result doesn't start with {)
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        # If no JSON object is found, continue to the next retry
                        print(f"No valid JSON object found, will retry...")
                        continue

                try:
                    result = json.loads(json_str)
                    if "suggestions" in result:
                        # Successfully found valid result, return
                        return result
                    else:
                        # JSON parsing successful but missing required field, continue retry
                        print(f"Missing suggestions field in JSON, will retry...")
                        continue
                except json.JSONDecodeError as e:
                    # JSON parsing failed, continue retry
                    print(f"JSON parsing failed: {str(e)}, will retry...")
                    continue

            except Exception as e:
                print(f"API call or processing error: {str(e)}, will retry...")
                # Continue to next retry

        # After all retries fail, return default value
        print("All retries failed, returning default suggestion")
        return {
            "suggestions": "Unable to obtain valid emotional analysis. Please check the story content and try again."}


class LiteraryStylist:
    """Enhance story creativity and novelty of plot"""

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    def check_story(self, story, guide_dict, max_retries=3):
        system_message = """You are a Literary Stylist - an expert focused on optimizing language expression and rhetorical effects.
        You analyze based on Stylistics theory, which studies how language choices create literary effects:
        1. Selection Theory - Literary style is the author's conscious choice among multiple linguistic possibilities
        2. Foregrounding - Highlighting specific expressions and effects by deviating from linguistic norms
        3. Grammar-Style Continuum - Grammatical structures directly influence stylistic effects
        4. Cohesion and Coherence - The organic unity between the surface structure and deep meaning of text
        5. Speech Acts and Pragmatic Effects - How language achieves specific communicative purposes

        Please strictly return JSON in the following format, without adding any extra text, comments, or code blocks:
        {
            "suggestions": "specific style improvement suggestions"
        }

        Very important:
        1. You must only return a JSON object in the above format, without any other text
        2. Do not add any descriptions, explanations, or code block markers (like ```) before or after the JSON
        3. Your response must be directly parsable by json.loads() without additional processing steps"""

        prompt = f"""As a Literary Stylist, please analyze the language style of the following story content based on Stylistics theory:
        {story}

        Please evaluate in depth from the following aspects:
        1. Vocabulary Choice - Analyze the precision, richness, and stylistic consistency of vocabulary
        2. Syntactic Variation - Evaluate the variation and rhythm of sentence length and structure
        3. Rhetorical Devices - Analyze the effects of metaphors, similes, symbolism, and other rhetorical devices
        4. Phonetic Effects - Examine the phonological, rhythmic, and prosodic qualities of the language
        5. Narrative Perspective - Analyze the consistency and effectiveness of the narrator's voice
        6. Style Compatibility - Evaluate whether the language style matches the story type, theme, and characters

        Please explain in detail the strengths and weaknesses of each aspect, and provide specific modification suggestions to enhance the text's literariness and expressiveness.

        Must return results in pure English JSON format, without adding any other text, comments, or code block markers, directly return:
        {{
        "suggestions": "Specific language style improvement suggestions based on Stylistics"
        }}

        Note: The returned JSON must be correctly formatted, without any escape errors or control characters, to ensure it can be parsed by a standard JSON parser."""

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)

                print(f"Literary effect (attempt {retry_count + 1}/{max_retries}): {raw_result}")

                # Clean JSON string - remove code block markers and control characters
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove all control characters that might cause JSON parsing to fail
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in ['\n', '\r', '\t'])

                # Try to extract JSON object (if result doesn't start with {)
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        # If no JSON object is found, continue to the next retry
                        print(f"No valid JSON object found, will retry...")
                        continue

                try:
                    result = json.loads(json_str)
                    if "suggestions" in result:
                        # Successfully found valid result, return
                        return result
                    else:
                        # JSON parsing successful but missing required field, continue retry
                        print(f"Missing suggestions field in JSON, will retry...")
                        continue
                except json.JSONDecodeError as e:
                    # JSON parsing failed, continue retry
                    print(f"JSON parsing failed: {str(e)}, will retry...")
                    continue

            except Exception as e:
                print(f"API call or processing error: {str(e)}, will retry...")
                # Continue to next retry

        # After all retries fail, return default value
        print("All retries failed, returning default suggestion")
        return {
            "suggestions": "Unable to obtain valid literary style analysis. Please check the story content and try again."}


class ReaderAdvocateAgent:
    """Evaluating story appeal and immersive experience from the reader's perspective"""

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    def check_story(self, story, guide_dict, max_retries=3):
        system_message = """You are a Reader's Advocate - an expert focused on evaluating story appeal from the perspective of ordinary readers.
        You analyze based on Narrative Transportation Theory, which studies how readers are "transported" into the story world:
        1. Attention Focus - Reader's cognitive resources are completely drawn into the story
        2. Emotional Involvement - Readers develop genuine emotional responses to characters and events
        3. Mental Imagery - Readers construct vivid images of story scenes and events in their minds
        4. Temporary Loss of Reality - Readers temporarily forget the existence of the real world
        5. Narrative Belief Change - Immersive experiences may influence readers' beliefs and attitudes

        Please strictly return JSON in the following format, without adding any extra text, comments, or code blocks:
        {
            "suggestions": "specific reader experience enhancement suggestions"
        }

        Very important:
        1. You must only return a JSON object in the above format, without any other text
        2. Do not add any descriptions, explanations, or code block markers (like ```) before or after the JSON
        3. Your response must be directly parsable by json.loads() without additional processing steps"""

        prompt = f"""As a Reader's Advocate, please analyze the appeal of the following story to ordinary readers based on Narrative Transportation Theory:
        {story}

        Please evaluate the story's immersion potential from the following aspects:
        1. Attention Hooks - Whether the story contains elements that immediately capture the reader's attention
        2. Emotional Connection - Whether characters and situations have sufficient emotional depth to evoke reader empathy
        3. Mental Imagery Stimulation - Whether descriptions are vivid and specific enough to create clear images in the reader's mind
        4. Narrative Fluency - Whether the story eliminates barriers that might interrupt the reader's immersive experience
        5. Suspense and Curiosity - Whether the story builds suspense elements that continuously attract readers to read forward
        6. World-Building Depth - Whether the story world is rich and coherent enough for readers to willingly immerse themselves in it

        Please provide specific improvement suggestions from the perspective of ordinary readers, avoiding technical terminology, focusing on enhancing the reader's immersive experience and reading pleasure.

        Must return results in pure English JSON format, without adding any other text, comments, or code block markers, directly return:
        {{
            "suggestions": "Specific suggestions for enhancing reader immersion experience"
        }}

        Note: The returned JSON must be correctly formatted, without any escape errors or control characters, to ensure it can be parsed by a standard JSON parser."""

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)

                print(f"Reader experience evaluation result (attempt {retry_count + 1}/{max_retries}): {raw_result}")

                # Clean JSON string - remove code block markers and control characters
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove all control characters that might cause JSON parsing to fail
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in ['\n', '\r', '\t'])

                # Try to extract JSON object (if result doesn't start with {)
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        # If no JSON object is found, continue to the next retry
                        print(f"No valid JSON object found, will retry...")
                        continue

                try:
                    result = json.loads(json_str)
                    if "suggestions" in result:
                        # Successfully found valid result, return
                        return result
                    else:
                        # JSON parsing successful but missing required field, continue retry
                        print(f"Missing suggestions field in JSON, will retry...")
                        continue
                except json.JSONDecodeError as e:
                    # JSON parsing failed, continue retry
                    print(f"JSON parsing failed: {str(e)}, will retry...")
                    continue

            except Exception as e:
                print(f"API call or processing error: {str(e)}, will retry...")
                # Continue to next retry

        # After all retries fail, return default value
        print("All retries failed, returning default suggestion")
        return {
            "suggestions": "Unable to obtain valid reader experience analysis. Please check the story content and try again."}


class SuggestionEditor:
    """Integrate the evaluation results of each agent to generate comprehensive modification suggestions"""

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    def integrate_suggestions(self, structure_result, emotional_result, style_result, reader_result, max_retries=3):

        system_message = """You are an Integration Coordinator - an expert focused on integrating multiple feedback sources and forming effective suggestions.
    You analyze based on The Wisdom of Crowds theory, which studies how collective decision-making can be superior to individual decisions:
    1. Cognitive Diversity - Perspectives from different viewpoints can cover multiple dimensions of a problem
    2. Independence Principle - Each evaluator provides independent judgments uninfluenced by other evaluators
    3. Decentralization - Evaluators make judgments based on their respective areas of expertise and local knowledge
    4. Aggregation Mechanism - Integrating diverse judgments into comprehensive conclusions

    Please strictly return JSON in the following format:
    {
        "integrated_suggestions": "Specific integrated modification suggestions",
        "priority_areas": ["Priority modification area 1", "Priority modification area 2", ...]
    }
    Note:
    1. Must only return a JSON object
    2. Do not include any additional text"""

        prompt = f"""As an Integration Coordinator, please integrate the following assessment results from different experts based on The Wisdom of Crowds theory:

    Structure Editor suggestions:
    {structure_result['suggestions']}

    Emotional Orchestrator suggestions:
    {emotional_result['suggestions']}

    Literary Stylist suggestions:
    {style_result['suggestions']}

    Reader's Advocate suggestions:
    {reader_result['suggestions']}

    Please integrate your analysis from the following aspects:
    1. Consensus Identification - Identify problem points commonly recognized by multiple experts
    2. Conflicting Viewpoint Coordination - Balance potentially contradictory suggestions
    3. Priority Assignment - Determine priorities based on the impact of issues on overall quality
    4. Comprehensive Solutions - Provide integrated suggestions that solve multiple problems simultaneously
    5. Implementation Feasibility - Ensure suggestions are operational and provide clear guidance

    Please return results in the following English JSON format:
    {{
        "integrated_suggestions": "Comprehensive modification suggestions",
        "priority_areas": ["Priority issue 1", "Priority issue 2",...]
    }}"""

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ]
                )

                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)

                print(f"Integrated suggestion results: {raw_result}")  # For debugging

                # Clean JSON string
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove control characters
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in '\n\r\t')

                # Try to extract JSON object
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)

                try:
                    result = json.loads(json_str)
                    if "integrated_suggestions" in result and "priority_areas" in result:
                        return result

                    # If only one field exists, try to supplement the other
                    if "integrated_suggestions" in result and "priority_areas" not in result:
                        # Extract key points from suggestions as priority areas
                        suggestions = result["integrated_suggestions"]
                        # Try to match numbered list items
                        areas = re.findall(r'\d+\.\s*([^。；\n.;]+)', suggestions)
                        if areas:
                            result["priority_areas"] = areas[:5]  # Take at most 5
                            return result
                        else:
                            result["priority_areas"] = ["Need to further clarify priority areas"]
                            return result

                    if "priority_areas" in result and "integrated_suggestions" not in result:
                        result[
                            "integrated_suggestions"] = "Please refer to the priority areas list as improvement focus"
                        return result

                    print(f"Missing required fields in parsed JSON, attempting retry...")
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")

                    # Try to extract the two fields separately
                    integrated_match = re.search(r'"integrated_suggestions"\s*:\s*"(.*?)(?:"\s*}|\"\s*,)', json_str,
                                                 re.DOTALL)
                    priority_match = re.search(r'"priority_areas"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)

                    if integrated_match or priority_match:
                        result = {}

                        if integrated_match:
                            integrated_suggestions = integrated_match.group(1).replace('\\"', '"').replace('\\n', '\n')
                            result["integrated_suggestions"] = integrated_suggestions
                        else:
                            result[
                                "integrated_suggestions"] = "Unable to extract specific suggestions, please refer to priority areas"

                        if priority_match:
                            # Try to parse priority areas list
                            priority_str = "[" + priority_match.group(1) + "]"
                            try:
                                priority_areas = json.loads(priority_str)
                                result["priority_areas"] = priority_areas
                            except:
                                # Manual parsing
                                priority_str = priority_match.group(1)
                                areas = re.findall(r'"([^"]+)"', priority_str)
                                if areas:
                                    result["priority_areas"] = areas
                                else:
                                    # Remove quotes, split by comma
                                    areas = [area.strip(' "\'') for area in priority_str.split(',')]
                                    result["priority_areas"] = areas
                        else:
                            # Extract key points from integrated_suggestions
                            if "integrated_suggestions" in result:
                                suggestions = result["integrated_suggestions"]
                                areas = re.findall(r'\d+\.\s*([^。；\n.;]+)', suggestions)
                                if areas:
                                    result["priority_areas"] = areas[:5]  # Take at most 5
                                else:
                                    result["priority_areas"] = ["Need to further clarify priority areas"]
                            else:
                                result["priority_areas"] = ["Unable to extract priority areas"]

                        return result

                    # Extract content directly from the original response
                    if "integrated_suggestions" in raw_result and "priority_areas" in raw_result:
                        # Try rough extraction of content
                        integrated_text = re.search(r'integrated_suggestions["\s:]*([^"{}[\]]+)', raw_result)
                        priority_text = re.search(r'priority_areas["\s:]*\[(.*?)\]', raw_result, re.DOTALL)

                        result = {}
                        if integrated_text:
                            result["integrated_suggestions"] = integrated_text.group(1).strip()
                        else:
                            result["integrated_suggestions"] = "Unable to extract specific suggestions"

                        if priority_text:
                            # Try parsing priority areas
                            areas_text = priority_text.group(1)
                            areas = re.findall(r'"([^"]+)"', areas_text)
                            if areas:
                                result["priority_areas"] = areas
                            else:
                                areas = [area.strip(' "\'') for area in areas_text.split(',')]
                                result["priority_areas"] = [a for a in areas if a]
                        else:
                            result["priority_areas"] = ["Unable to extract priority areas"]

                        return result

                # If maximum retries reached and still unable to parse, try extracting information from the original text
                if retry_count == max_retries - 1:
                    text = raw_result.replace('```json', '').replace('```', '')

                    # Try to find suggestion parts
                    suggestions = ""
                    priority_areas = []

                    # Look for integrated suggestions
                    sugg_match = re.search(
                        r'(?:Comprehensive suggestions|Integrated suggestions|integrated_suggestions)[:：]?\s*(.*?)(?=\n\n|Priority|priority_areas|$)',
                        text, re.DOTALL)
                    if sugg_match:
                        suggestions = sugg_match.group(1).strip()
                    else:
                        # Try to extract the first meaningful paragraph
                        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                        if paragraphs:
                            suggestions = paragraphs[0]

                    # Look for priority areas
                    areas_match = re.search(
                        r'(?:Priority areas|Priority issues|priority_areas)[:：]?\s*(.*?)(?=\n\n|$)', text, re.DOTALL)
                    if areas_match:
                        areas_text = areas_match.group(1)
                        # Try to extract list items
                        areas = re.findall(r'[（(]?\d+[)）.、]?\s*([^，。；\n,;]+)', areas_text)
                        if areas:
                            priority_areas = areas
                        else:
                            # Try splitting by comma or newline
                            areas = re.split(r'[,，\n]', areas_text)
                            priority_areas = [a.strip() for a in areas if a.strip()]

                    if not suggestions and not priority_areas:
                        # Last attempt: divide text into key points
                        points = re.findall(r'[（(]?\d+[)）.、]?\s*([^，。；\n,;]+)', text)
                        if points:
                            suggestions = "Please note the following key issues: " + "; ".join(points[:3])
                            priority_areas = points[:5]

                    if suggestions or priority_areas:
                        return {
                            "integrated_suggestions": suggestions or "Please refer to the priority areas list",
                            "priority_areas": priority_areas or ["Need to clarify improvement focus"]
                        }

                print(f"Attempt {retry_count + 1}, will retry...")

            except Exception as e:
                print(f"API call error: {str(e)}")
                if retry_count == max_retries - 1:
                    break

        # If all retries fail, return default value
        print("All retries failed, returning default suggestions")
        return {
            "integrated_suggestions": "Unable to integrate expert suggestions. Please check each evaluation result and try again.",
            "priority_areas": ["Overall story structure", "Emotional expression", "Language style", "Reader experience",
                               "Narrative fluency"]
        }


class StoryEditorAgent:
    """Story editor, compares the quality of the original story and the revised story and selects the better version"""

    def __init__(self, client):
        self.client = client

    def save_log(self, request_msg, response_msg):
        """保存日志到数据库"""
        # 当需要时才获取数据库连接
        db_connection = pool.get_connection()
        cursor = db_connection.cursor()

        try:
            timestamp = datetime.now()
            insert_query = """
            INSERT INTO main (timestamp, request_message, response_message)
            VALUES (%s, %s, %s)
            """
            values = (timestamp, request_msg, response_msg)

            cursor.execute(insert_query, values)
            db_connection.commit()
        except Exception as e:
            print(f"保存日志时出错: {str(e)}")
            db_connection.rollback()
        finally:
            # 操作完成后立即关闭连接，释放回连接池
            cursor.close()
            db_connection.close()

    def compare_stories(self, original_story, revised_story, max_retries=3):
        system_message = """You are a professional story evaluation expert, skilled in fairly and objectively comparing the quality of different story versions.
    Your task is to evaluate two story versions based on four key dimensions, and return the results in strict English JSON format.
    Do not include any additional explanations, comments, or analysis, only return the requested English JSON format."""

        prompt = f"""Please compare the following two story versions, evaluating their performance across four dimensions.

    Story A:
    {original_story}

    Story B:
    {revised_story}

    Evaluation task:
    1) Overall, which story version has stronger coherence? A / B
    2) Overall, which story version has better writing style consistency? A / B
    3) Overall, which story version is more interesting/engaging? A / B
    4) Overall, which story version has richer creative expression? A / B

    Please return your evaluation results in the exact English JSON format below:
    {{
      "verdict": "1:your choice, 2:your choice, 3:your choice, 4:your choice",
      "explanation": "Brief overall judgment explanation (no more than 100 words)"
    }}

    Very important:
    1. Maintain the exact English JSON format
    2. Your choice must be A or B, do not use any other symbols or text
    3. The value of the verdict field must use the exact format "1:your choice, 2:your choice, 3:your choice, 4:your choice"
    """

        for retry_count in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="glm-4-air",
                    messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt}]
                )

                # Process response
                raw_result = response.choices[0].message.content

                full_request_msg = f"{system_message} {prompt}"

                self.save_log(full_request_msg, raw_result)

                print(f"Story comparison result: {raw_result}")

                # Clean JSON string
                json_str = re.sub(r'```(?:json)?\s*|\s*```', '', raw_result)
                json_str = json_str.strip()

                # Remove control characters
                json_str = ''.join(ch for ch in json_str if ord(ch) >= 32 or ch in '\n\r\t')

                # Try to extract JSON object
                if not json_str.startswith('{'):
                    match = re.search(r'{.*}', json_str, re.DOTALL)
                    if match:
                        json_str = match.group(0)

                try:
                    result = json.loads(json_str)

                    # Parse verdict field, calculate which version wins
                    if "verdict" in result:
                        verdict = result["verdict"]
                        choices = re.findall(r'\d+:([AB])', verdict)

                        # Calculate how many wins for A and B respectively
                        a_wins = choices.count("A")
                        b_wins = choices.count("B")

                        # Determine final version choice
                        final_choice = "B" if b_wins >= a_wins else "A"  # If tie, choose B (revised version)

                        explanation = result.get("explanation", "No explanation provided")

                        return {
                            "selected_version": final_choice,
                            "a_wins": a_wins,
                            "b_wins": b_wins,
                            "verdict_details": verdict,
                            "explanation": explanation
                        }
                    else:
                        # Try to extract verdict using regular expression
                        verdict_match = re.search(r'"verdict"\s*:\s*"([^"]*)"', json_str)
                        explanation_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', json_str)

                        if verdict_match:
                            verdict = verdict_match.group(1)
                            choices = re.findall(r'\d+:([AB])', verdict)

                            a_wins = choices.count("A")
                            b_wins = choices.count("B")

                            final_choice = "B" if b_wins >= a_wins else "A"

                            explanation = "No explanation provided"
                            if explanation_match:
                                explanation = explanation_match.group(1)

                            return {
                                "selected_version": final_choice,
                                "a_wins": a_wins,
                                "b_wins": b_wins,
                                "verdict_details": verdict,
                                "explanation": explanation
                            }

                    # If no verdict field, try to extract judgments directly from text
                    choices = re.findall(r'(\d+)\s*[:.]\s*([AB])', raw_result)
                    if choices:
                        verdict_parts = []
                        a_wins = 0
                        b_wins = 0

                        for num, choice in choices:
                            verdict_parts.append(f"{num}:{choice}")
                            if choice == "A":
                                a_wins += 1
                            elif choice == "B":
                                b_wins += 1

                        verdict = ", ".join(verdict_parts)
                        final_choice = "B" if b_wins >= a_wins else "A"

                        # Try to extract explanation
                        expl_match = re.search(r'(?:explanation|explanation|judgment)[:：]?\s*(.{10,100})', raw_result,
                                               re.IGNORECASE)
                        explanation = expl_match.group(1) if expl_match else "No detailed explanation provided"

                        return {
                            "selected_version": final_choice,
                            "a_wins": a_wins,
                            "b_wins": b_wins,
                            "verdict_details": verdict,
                            "explanation": explanation
                        }

                    print(f"Missing verdict field in parsed JSON, attempting retry...")

                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")

                    # Try to extract judgment results directly from text
                    choices = re.findall(r'(\d+)\s*[:.]\s*([AB])', raw_result)
                    if choices:
                        verdict_parts = []
                        a_wins = 0
                        b_wins = 0

                        for num, choice in choices:
                            verdict_parts.append(f"{num}:{choice}")
                            if choice == "A":
                                a_wins += 1
                            elif choice == "B":
                                b_wins += 1

                        verdict = ", ".join(verdict_parts)
                        final_choice = "B" if b_wins >= a_wins else "A"

                        # Try to extract explanation
                        expl_match = re.search(r'(?:explanation|explanation|judgment)[:：]?\s*(.{10,100})', raw_result,
                                               re.IGNORECASE)
                        explanation = expl_match.group(1) if expl_match else "No detailed explanation provided"

                        return {
                            "selected_version": final_choice,
                            "a_wins": a_wins,
                            "b_wins": b_wins,
                            "verdict_details": verdict,
                            "explanation": explanation
                        }

                # If maximum retries reached and still unable to parse, look for clues in the original text
                if retry_count == max_retries - 1:
                    # Look for any evaluations containing A or B
                    choices = re.findall(r'(\d+)\s*[:.]\s*([AB])', raw_result)
                    if choices:
                        verdict_parts = []
                        a_wins = 0
                        b_wins = 0

                        for num, choice in choices:
                            if num in ["1", "2", "3", "4"]:  # Ensure it's the dimension we're looking for
                                verdict_parts.append(f"{num}:{choice}")
                                if choice == "A":
                                    a_wins += 1
                                elif choice == "B":
                                    b_wins += 1

                        if verdict_parts:
                            verdict = ", ".join(verdict_parts)
                            final_choice = "B" if b_wins >= a_wins else "A"

                            # Extract a possible explanation
                            paragraphs = [p for p in raw_result.split("\n\n") if len(p) > 20 and len(p) < 150]
                            explanation = paragraphs[-1] if paragraphs else "Could not extract explanation"

                            return {
                                "selected_version": final_choice,
                                "a_wins": a_wins,
                                "b_wins": b_wins,
                                "verdict_details": verdict,
                                "explanation": explanation
                            }

                print(f"Attempt {retry_count + 1}, will retry...")

            except Exception as e:
                print(f"API call error: {str(e)}")
                if retry_count == max_retries - 1:
                    break

        # If all retries fail, return default value
        print("All retries failed, returning default result")
        return {
            "selected_version": "B",  # Default to revised version in error cases
            "a_wins": 0,
            "b_wins": 4,
            "verdict_details": "Parsing failed",
            "explanation": "Unable to obtain valid comparison results, defaulting to revised version"
        }


def create_story_generator(api_key):
    """Creates and returns a story generator instance"""
    client = ZhipuAI(api_key=api_key)
    return StoryGenerator(client)


if __name__ == "__main__":
    print("This module is designed to be imported and used in a web application.")
    print("Please run the web server instead of running this file directly.")

