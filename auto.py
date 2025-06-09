from playwright.sync_api import sync_playwright, TimeoutError
import pandas as pd
import time
import json
import os
import logging
import sys


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("experiment_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StoryExperimentAutomation:
    def __init__(self, excel_path, url="http://localhost:9090/#/pages/index"):

        self.excel_path = excel_path
        self.url = url
        self.premises = self._load_premises()
        self.progress_file = "automation_progress.json"
        self.current_index = self._load_progress()
        self.retry_limit = 3

    def _load_premises(self):

        try:
            df = pd.read_excel(self.excel_path)
            logger.info(f"run  {len(df)} premise")
            return df
        except Exception as e:
            logger.error(f"loading error: {e}")
            raise

    def _load_progress(self):

        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
                logger.info(f"{progress['current_index']} premise")
                return progress['current_index']
        return 0

    def _save_progress(self, index):

        with open(self.progress_file, 'w') as f:
            json.dump({'current_index': index}, f)

    def run(self):

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            try:

                page.goto(self.url)
                page.wait_for_load_state("networkidle")

                page.wait_for_timeout(8000)


                for i in range(self.current_index, len(self.premises)):
                    premise_index = i
                    logger.info(f"run{premise_index + 1}/{len(self.premises)} premise")


                    for retry in range(self.retry_limit):
                        try:
                            self._process_premise(page, premise_index)
                            self._save_progress(premise_index + 1)

                            page.wait_for_timeout(8000)
                            break
                        except Exception as e:
                            logger.error(f"{retry + 1}/{self.retry_limit}): {e}")


                            if retry == self.retry_limit - 1:
                                logger.error(f"retry max，skip current premise")
                                self._save_progress(premise_index + 1)

                                try:
                                    page.goto(self.url)
                                    page.wait_for_load_state("networkidle")
                                    page.wait_for_timeout(8000)
                                except:
                                    logger.error("reload explorer")

                                    context.close()
                                    browser.close()
                                    browser = p.chromium.launch(headless=False)
                                    context = browser.new_context()
                                    page = context.new_page()
                                    page.goto(self.url)
                                    page.wait_for_load_state("networkidle")
                                    page.wait_for_timeout(8000)
                            else:

                                try:
                                    page.goto(self.url)
                                    page.wait_for_load_state("networkidle")
                                    page.wait_for_timeout(8000)
                                except:
                                    logger.error("retry")

                logger.info("all premise complete")
            finally:
                context.close()
                browser.close()

    def _process_premise(self, page, premise_index):

        max_story_number = self._get_max_story_number(page)
        new_story_number = max_story_number + 1


        logger.info(f"将处理故事编号 #{new_story_number}，使用premise_index={premise_index}")


        page.wait_for_timeout(5000)


        self._create_new_story(page, new_story_number)


        page.wait_for_timeout(8000)


        self._click_write_story(page, new_story_number)


        page.wait_for_timeout(10000)


        self._create_story_with_premise(page, new_story_number, premise_index)


        page.wait_for_timeout(5000)


        self._generate_complete_story(page)


        self._wait_for_story_completion(page)


        self._go_back_to_list(page)

    def _get_max_story_number(self, page):

        logger.info("Detecting the current maximum story number")

        page.wait_for_selector(".list-item", timeout=100000, state="visible")

        page.wait_for_timeout(5000)


        if page.query_selector(".empty-container"):
            logger.info("no exist story")
            return 0


        titles = page.eval_on_selector_all(".list-item .title", """(elements) => {
            return elements.map(el => el.textContent);
        }""")


        story_numbers = []
        for title in titles:
            try:
                num = int(title.strip())
                story_numbers.append(num)
            except:
                pass

        if not story_numbers:
            return 0

        max_number = max(story_numbers) if story_numbers else 0
        logger.info(f"{max_number}story")
        return max_number

    def _create_new_story(self, page, story_number):

        logger.info(f"new story {story_number}")


        page.wait_for_timeout(3000)


        page.click(".add-button")
        page.wait_for_timeout(3000)


        page.wait_for_selector(".uni-popup-dialog", state="visible")
        page.wait_for_timeout(2000)

        page.fill(".uni-popup-dialog input", str(story_number))
        page.wait_for_timeout(2000)


        page.click(".uni-dialog-button-text:has-text('确定')")
        page.wait_for_timeout(3000)


        if page.query_selector(".uni-popup-dialog"):
            page.click(".uni-dialog-button")
            page.wait_for_timeout(3000)


        page.wait_for_selector(".uni-popup-dialog", state="hidden", timeout=10000)


        page.wait_for_timeout(8000)

    def _click_write_story(self, page, story_number):

        logger.info(f"click #{story_number} button")

        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(8000)


        page.wait_for_selector(".list-item", state="visible", timeout=10000)
        page.wait_for_timeout(5000)

        try:
            logger.info("try click write story button")


            write_buttons = page.query_selector_all(".action-btn.write")
            if write_buttons:
                logger.info(f"find {len(write_buttons)} button")
                write_buttons[-1].click()
                logger.info("click success")
            else:
                raise Exception("no button")

        except Exception as e:
            logger.error(f"click button error {e}")

            page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const writeBtn = btns.find(btn => btn.textContent.includes('generate story'));
                if (writeBtn) writeBtn.click();
            }""")


        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(10000)


        if not page.query_selector(".action-button"):
            logger.warning("use url to navigate")

            generation_url = f"{self.url.replace('#/pages/index', '')}#/pages/generation/index?novelId={story_number}"
            logger.info(f"navigate to {generation_url}")
            page.goto(generation_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(10000)

    def _create_story_with_premise(self, page, story_number, premise_index):

        logger.info(f"new story {story_number}")

        try:

            page.wait_for_timeout(5000)


            page.wait_for_selector(".action-button", timeout=10000)
            page.click(".action-button")
            page.wait_for_timeout(3000)


            page.wait_for_selector(".dialog-content", state="visible", timeout=10000)
            page.wait_for_timeout(3000)


            page.wait_for_selector(".segmented-control__item--button--active", timeout=10000)
            page.wait_for_timeout(2000)


            adjusted_index = story_number - 1


            if 0 <= adjusted_index < len(self.premises):
                row = self.premises.iloc[adjusted_index]


                premise_column = None
                for col in self.premises.columns:
                    if 'premise' in col.lower() or 'content' in col.lower() or 'text' in col.lower():
                        premise_column = col
                        break

                if premise_column:
                    premise_text = str(row[premise_column])
                else:

                    second_col = self.premises.columns[1] if len(self.premises.columns) > 1 else None
                    if second_col:
                        premise_text = str(row[second_col])
                    else:
                        premise_text = f"Default premise for story #{story_number}"
            else:
                premise_text = f"Default premise for story #{story_number} - index out of range"

            logger.info(f"story {story_number} 's premise: {premise_text[:100]}...")


            page.fill("textarea", premise_text)
            page.wait_for_timeout(5000)

        except Exception as e:
            logger.error(f"input premise error{e}, story_number={story_number}")
            raise

    def _generate_complete_story(self, page):

        logger.info("click auto generate story")


        page.wait_for_timeout(10000)


        html_content = page.content()
        logger.info("check button...")

        button_check = page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            const buttonTexts = Array.from(buttons).map(b => ({
                text: b.textContent.trim(),
                type: b.getAttribute('type'),
                tag: b.tagName
            }));

            // find uni-button element
            const uniButtons = document.querySelectorAll('uni-button');
            const uniButtonTexts = Array.from(uniButtons).map(b => ({
                text: b.textContent.trim(),
                type: b.getAttribute('type'),
                tag: b.tagName
            }));

            return {
                buttons: buttonTexts,
                uniButtons: uniButtonTexts,
                hasWarnButton: !!document.querySelector('button[type="warn"], uni-button[type="warn"]'),
                hasTargetText: Array.from(document.querySelectorAll('*')).some(el => 
                    el.textContent.includes('automatic generate all story'))
            };
        }""")

        logger.info(f"search result {button_check}")


        success = False


        try:
            logger.info("try uni-button[type='warn']")
            warn_button = page.query_selector("uni-button[type='warn']")
            if warn_button:
                logger.info("find uni-button[type='warn'] button.")
                warn_button.click()
                page.wait_for_timeout(2000)  # wait click
                success = True
                logger.info("click success")
        except Exception as e:
            logger.warning(f"click fail: {e}")

        if not success:
            try:
                logger.info("try click button[type='warn']")
                warn_button = page.query_selector("button[type='warn']")
                if warn_button:
                    logger.info("find button[type='warn']button")
                    warn_button.click()
                    page.wait_for_timeout(2000)  # 等待点击生效
                    success = True
                    logger.info("click success")
            except Exception as e:
                logger.warning(f"click fail: {e}")

        if not success:
            try:
                logger.info("try click")
                result = page.evaluate("""() => {
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        if (el.textContent.includes('automatic generate all story')) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }""")

                if result:
                    success = True
                    logger.info("click success")
                    page.wait_for_timeout(2000)  # 等待点击生效
            except Exception as e:
                logger.warning(f"click fail: {e}")


        if not success:
            try:
                logger.info("find click")
                result = page.evaluate("""() => {

                    const buttons = [
                        ...document.querySelectorAll('button'),
                        ...document.querySelectorAll('uni-button'),
                        ...document.querySelectorAll('.uni-button')
                    ];


                    for (const btn of buttons) {
                        if (btn.getAttribute('type') === 'warn' || 
                            btn.classList.contains('uni-button-warning')) {
                            btn.click();
                            console.log('click warn button');
                            return 1;
                        }
                    }


                    if (buttons.length > 0) {
                        buttons[0].click();
                        console.log('click button');
                        return 2;
                    }

                    return 0;
                }""")

                if result > 0:
                    success = True
                    logger.info(f"click type {result} button")
                    page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"click fail: {e}")


        if not success:
            logger.error("try next")
        else:
            logger.info("click success")


        page.wait_for_timeout(10000)


        try:
            page.wait_for_selector("button[loading='true'], uni-button[loading='true']", timeout=10000)
            logger.info("story start")
        except Exception as e:
            logger.warning(f"continue {e}")

    def _wait_for_story_completion(self, page):

        logger.info("wait")

        try:

            page.wait_for_selector(".uni-modal", timeout=18000000)

            page.wait_for_timeout(5000)

            try:
                page.click(".uni-modal button")
                logger.info("click fail")
            except Exception as e:
                logger.warning(f"click fail: {e}")

                page.evaluate("""() => {
                    const buttons = document.querySelectorAll('.uni-modal button');
                    if (buttons.length > 0) buttons[0].click();
                }""")


            page.wait_for_selector(".uni-modal", state="hidden", timeout=30000)


            page.wait_for_timeout(5000)

        except Exception as e:
            logger.warning(f"wait error: {e}")

            try:
                page_content = page.content()
                if "loading='true'" not in page_content:
                    logger.info("generation complete")
                else:

                    page.evaluate("""() => {
                        const modals = document.querySelectorAll('.uni-modal');
                        if (modals.length > 0) {
                            const buttons = modals[0].querySelectorAll('button');
                            if (buttons.length > 0) buttons[0].click();
                        }
                    }""")
                    logger.info("close window")
            except Exception as inner_e:
                logger.error(f"check fail: {inner_e}")

    def _go_back_to_list(self, page):

        logger.info("back to story list")

        try:

            page.wait_for_timeout(5000)


            try:
                if page.query_selector(".dialog-content"):
                    page.click(".close-btn")
                    page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"close fail: {e}")

            page.goto(self.url)
            page.wait_for_load_state("networkidle")

            page.wait_for_timeout(8000)

            logger.info("back to list")
        except Exception as e:
            logger.error(f"back fail: {e}")

            try:
                page.goto(self.url)
                page.wait_for_timeout(8000)
            except:
                logger.error("back fail")
                raise



if __name__ == "__main__":
    try:
        automation = StoryExperimentAutomation("D:\\dataset.xlsx")
        automation.run()
    except KeyboardInterrupt:
        logger.info("user terminate the process")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"process error: {e}")
        sys.exit(1)