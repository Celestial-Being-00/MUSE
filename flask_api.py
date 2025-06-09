from flask import Flask, request, jsonify
from flask_cors import CORS
from main_db import create_story_generator, WritingGuide  # 修改导入
import os
import logging
import json
from datetime import datetime, timedelta
from threading import Timer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


story_generators = {}
session_timestamps = {}

app = Flask(__name__)
CORS(app)

API_KEY = "your api key"



def create_response(code, message, data=None):
    return jsonify({
        'code': str(code),
        'message': message,
        'data': data
    })


@app.route('/api/initialize', methods=['POST'])
def initialize_story():

    try:
        data = request.json
        logger.info("Received initialization request, data:%s", data)

        theme = data.get('theme')
        content = data.get('content')
        session_id = os.urandom(16).hex()


        generator = create_story_generator(API_KEY)


        generator.writing_guide = WritingGuide()

        if theme:
            generator.original_theme = theme
            generator.story_theme = theme
        elif content:
            generator.writing_guide.set_complete_guide(content)
        else:
            return create_response(400, 'Please provide a story topic or writing guide content')

        story_generators[session_id] = generator
        session_timestamps[session_id] = datetime.now()

        logger.info(f"Initialization successful，session_id: {session_id}")
        return create_response(200, 'Story generator initialized successfully', {'session_id': session_id})
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}", exc_info=True)
        return create_response(500, f'Initialization failed: {str(e)}')


@app.route('/api/generate-guide', methods=['POST'])
def generate_guide():

    try:
        data = request.json
        session_id = data.get('session_id')
        section = data.get('section', 1)

        if not session_id:
            return create_response(400, 'Please provide session_id')

        generator = story_generators.get(session_id)
        if not generator:
            return create_response(404, 'No corresponding story generator instance found')


        if section == 1:
            guide_content = {
                'genre_style': generator.analyze_genre_and_style(),
                'background': generator.generate_background(),
                'characters': generator.generate_characters(),
                #'core_plot': generator.generate_core_plot(),
                'plot_planning': generator.generate_plot_planning(),
                'narrative_style': generator.generate_narrative_style()
            }
            print(guide_content)
        else:
            previous_stories = generator.get_previous_stories()

            guide_content = {
                'genre_style': generator.analyze_genre_and_style(),
                'narrative_style': generator.writing_guide.narrative_style,
                #'core_plot': generator.writing_guide.core_plot
            }

            if previous_stories:
                summary = generator.writing_guide.generate_story_summary(
                    generator.client,
                    previous_stories
                )
                guide_content['summary'] = summary

                guide_content.update({
                    'background': generator.update_background(previous_stories),
                    'characters': generator.update_characters(previous_stories),
                    'plot_planning': generator.update_plot_planning(
                        #previous_stories=previous_stories,
                        genre_style=generator.analyze_genre_and_style(),
                        background=generator.writing_guide.background,
                        characters=generator.writing_guide.characters,
                        #core_plot=generator.writing_guide.core_plot,
                        plot_planning=generator.writing_guide.plot_planning
                    )
                })


        writing_guide_text = format_guide_content(guide_content)
        guide_content['writing_guide'] = writing_guide_text

        return create_response(200, 'Writing guide generated successfully', {
            'content': guide_content
        })

    except Exception as e:
        return create_response(500, f'Failed to generate writing guide: {str(e)}')



def format_guide_content(guide_content):

    writing_guide_text = ""

    #if guide_content.get('summary'):
        #writing_guide_text += f"{guide_content['summary']}\n\n"
    if guide_content.get('genre_style'):
        writing_guide_text += f"{guide_content['genre_style']}\n\n"
    if guide_content.get('background'):
        writing_guide_text += f"{guide_content['background']}\n\n"
    if guide_content.get('characters'):
        writing_guide_text += f"{guide_content['characters']}\n\n"
    #if guide_content.get('core_plot'):
        #writing_guide_text += f"{guide_content['core_plot']}\n\n"
    if guide_content.get('plot_planning'):
        writing_guide_text += f"{guide_content['plot_planning']}\n\n"
    if guide_content.get('narrative_style'):
        writing_guide_text += f"{guide_content['narrative_style']}\n\n"

    return writing_guide_text.rstrip()


@app.route('/api/initialize-story-generation', methods=['POST'])
def initialize_story_generation():
    """初始化故事生成环境"""
    try:
        logger.info("Start initializing the story generation environment")
        session_id = os.urandom(16).hex()


        generator = create_story_generator(API_KEY)


        generator.writing_guide = WritingGuide()


        story_generators[session_id] = generator
        session_timestamps[session_id] = datetime.now()

        logger.info(f"The story generation environment was initialized successfully，session_id: {session_id}")
        return create_response(200, 'The story generation environment was initialized successfully', {'session_id': session_id})
    except Exception as e:
        logger.error(f"the story generation environment was initialize successfully: {str(e)}", exc_info=True)
        return create_response(500, f'Initialization failed: {str(e)}')


@app.route('/api/generate-story', methods=['POST'])
def generate_story():

    try:
        data = request.json
        logger.info("Receive a request to generate a story")

        session_id = data.get('session_id')
        writing_guide = data.get('writing_guide')

        if not session_id or not writing_guide:
            return create_response(400, 'Missing required parameters')

        generator = story_generators.get(session_id)
        if not generator:
            return create_response(404, 'No corresponding story generator instance found')


        if isinstance(writing_guide, str):
            try:
                writing_guide = json.loads(writing_guide)
            except json.JSONDecodeError:
                writing_guide = {"content": writing_guide}


        logger.info("Start generating story content and headlines")
        result = generator.generate_story_content(writing_guide)


        if not result or not isinstance(result, dict):
            logger.error("Generated story format is incorrect")
            return create_response(500, 'Generated story format is incorrect')

        content = result.get('content', '')
        title = result.get('title', 'no title')

        if not content:
            logger.error("The generated story content is empty")
            return create_response(500, 'The generated story content is empty')


        logger.info(f"Story and headline generation success: {title}")
        return create_response(200, 'Story generation success', {
            'story': content,
            'title': title
        })

    except Exception as e:
        logger.error(f"Failed to generate story: {str(e)}", exc_info=True)
        return create_response(500, f'Failed to generate story: {str(e)}')







def is_valid_session(session_id):

    return session_id in story_generators


@app.route('/api/next-chapter', methods=['POST'])
def generate_next_chapter():

    try:
        data = request.get_json()
        logger.info("Receive a request to generate the next section, data:%s", data)


        session_id = data.get('session_id')
        current_guide = data.get('current_guide')
        story_content = data.get('story_content')


        if not session_id:
            return create_response(400, 'Please provide session_id')


        if not is_valid_session(session_id):
            logger.error(f"Invalid session_id: {session_id}")
            return create_response(401, 'The session has expired, please reinitialize')


        if not current_guide or not story_content:
            return create_response(400, 'Missing required parameters')

        generator = story_generators.get(session_id)
        if not generator:
            return create_response(404, 'No corresponding story generator instance found')


        if hasattr(generator, 'is_completed') and generator.is_completed:
            return create_response(200, '故事已完结', {
                'is_completed': True,
                'reason': getattr(generator, 'completion_reason', '故事已自然结束')
            })


        try:
            if isinstance(current_guide, str):
                current_guide = json.loads(current_guide)
            generator.core_plot = current_guide.get('core_plot', {})
        except json.JSONDecodeError:
            return create_response(400, 'Invalid writing guide format')


        generator.current_plot = story_content


        completion_status = generator.check_story_completion(current_guide)
        if completion_status["is_completed"]:

            generator.is_completed = True
            generator.completion_reason = completion_status["reason"]

            return create_response(200, '故事已完结', {
                'completed': True,
                'reason': completion_status["reason"]
            })


        guide_content = {
            'genre_style': current_guide.get('genre_style'),
            'core_plot': current_guide.get('core_plot'),

            'narrative_style': current_guide.get('narrative_style'),
            'summary': generator.writing_guide.generate_story_summary(
                generator.client,
                story_content
            ),
            'background': generator.update_background(story_content,current_guide.get('background')),
            'characters': generator.update_characters(story_content,current_guide.get('characters')),
            'plot_planning': generator.update_plot_planning(
                previous_stories=story_content,
                genre_style=generator.analyze_genre_and_style(),
                background=generator.writing_guide.background,
                characters=generator.writing_guide.characters,
                core_plot=current_guide.get('core_plot'),
                plot_planning=current_guide.get('plot_planning')
            )
        }


        updated_narrative = generator.update_narrative_style(guide_content['plot_planning'])
        guide_content['narrative_style'] = updated_narrative


        writing_guide_text = "\n\n".join(
            [f"{section}：\n{content}"
             for section, content in [
                 #("summary", guide_content.get('summary')),
                 ("genre_style", guide_content.get('genre_style')),
                 ("background", guide_content.get('background')),
                 ("characters", guide_content.get('characters')),
                 #("core_plot", guide_content.get('core_plot')),
                 ("plot_planning", guide_content.get('plot_planning')),
                 ("narrative_style", guide_content.get('narrative_style'))
             ] if content]
        )

        guide_content['writing_guide'] = writing_guide_text.rstrip()

        logger.info("Next section Writing Guide generated successfully")
        return create_response(200, 'Next section Writing Guide generated successfully', {
            'content': guide_content,
            'completed': False
        })

    except Exception as e:
        logger.error(f"Next section writing guide generation failed: {str(e)}", exc_info=True)
        return create_response(500, f'Next section writing guide generation failed: {str(e)}')




@app.route('/api/cleanup', methods=['POST'])
def cleanup_session():

    try:
        data = request.get_json()
        logger.info("Received a cleanup session request")

        session_id = data.get('session_id')
        if not session_id:
            return create_response(400, 'Please provide session_id')


        if session_id in story_generators:

            generator = story_generators.pop(session_id)
            del generator


            if session_id in session_timestamps:
                del session_timestamps[session_id]

            logger.info(f"Successfully cleaned up the session: {session_id}")
            return create_response(200, 'Session cleanup successful')
        else:
            logger.warning(f"No session found to clean up: {session_id}")
            return create_response(404, 'The specified session was not found')

    except Exception as e:
        logger.error(f"Failed to clean up session: {str(e)}", exc_info=True)
        return create_response(500, f'Failed to clean up session: {str(e)}')



def cleanup_expired_sessions():

    current_time = datetime.now()
    expired_sessions = []

    for session_id, timestamp in session_timestamps.items():
        if current_time - timestamp > timedelta(hours=2):
            expired_sessions.append(session_id)

    for session_id in expired_sessions:
        if session_id in story_generators:
            del story_generators[session_id]
        if session_id in session_timestamps:
            del session_timestamps[session_id]

        logger.info(f"Clean up expired sessions: {session_id}")

    Timer(600000, cleanup_expired_sessions).start()



cleanup_expired_sessions()




if __name__ == '__main__':
    logger.info("Start the Flask application...")
    app.run(debug=True, port=5000)