Our MUSE project is divided into three parts, ① front-end ② back-end ③ Python api
This part shows the Python code of MUSE

The main python code is in main_db.py, and flask_api.py encapsulates the main_db.py code as an api for front-end and back-end calls

The front-end and back-end parts are developed based on the open source project ruoyi: https://ruoyi.vip/
Front-end code link: https://github.com/Celestial-Being-00/MUSE_Frontend
Back-end code link: https://github.com/Celestial-Being-00/MUSE_backend

Project operation process:
① Run flask_api.py code
② Run Redis6, and then run the Ruoyi\RuoYi-Vue-springboot3\ruoyi-admin\src\main\java\com\ruoyi\RuoYiApplication.java file in the back-end project to start the back-end.
③ Use HBuilder X to run the front-end project and choose to run to the browser. You can start the front-end project.
④ Log in to the project on the opened web page. On the story list page, you can click New Story, enter your story name, click Save, and then click the button Generate Story to enter the story writing page. Enter the premise on the story writing page. After waiting for a few minutes, the writing guide for the first section will be generated. Click Generate Story below the Writing Guide pop-up window to generate the story corresponding to the first section... and so on, until all the story sections are generated.

If an error occurs during project operation, you can find a solution in the ruoyi project
