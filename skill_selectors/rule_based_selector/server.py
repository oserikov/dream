#!/usr/bin/env python

import logging
import time
from typing import List

from flask import Flask, request, jsonify
from os import getenv
import sentry_sdk

from common.constants import CAN_NOT_CONTINUE, CAN_CONTINUE, MUST_CONTINUE


sentry_sdk.init(getenv('SENTRY_DSN'))

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class RuleBasedSelector():
    wh_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how"}
    first_question_words = {
        "do", "have", "did", "had", "are", "is", "am", "will",
        "would", "should", "shall", "may", "might", "can", "could"
    }

    sensitive_topics = {"Politics", "Celebrities", "Religion", "Sex_Profanity", "Sports",
                        "News", "Psychology"
                        }
    # `General_ChatIntent` sensitive in case when `?` in reply
    sensitive_dialogacts = {"Opinion_RequestIntent", "General_ChatIntent"
                            }

    def __init__(self, **kwargs):
        logger.info("Skill selector Initialized")

    def _is_question(self, tokens):
        return tokens[0] in self.first_question_words or len(set(tokens).intersection(self.wh_words)) > 0

    def __call__(self, states_batch, **kwargs) -> List[List[str]]:

        skill_names = []

        for dialog in states_batch:
            skills_for_uttr = []
            reply = dialog['utterances'][-1]['text'].replace("\'", " \'").lower()
            # tokens = reply.split()

            # TODO: opinion_request/yes/no response
            intent_detected = any([v['detected'] == 1 for k, v in
                                   dialog['utterances'][-1]['annotations']['intent_catcher'].items()
                                   if k not in {'opinion_request', 'yes', 'no', 'tell_me_more', 'doing_well',
                                                'weather_forecast_intent'}])
            cobot_topics = set(dialog['utterances'][-1]['annotations']['cobot_topics']['text'])
            sensitive_topics_detected = any([t in self.sensitive_topics for t in cobot_topics])
            cobot_dialogacts = dialog['utterances'][-1]['annotations']['cobot_dialogact']['intents']
            cobot_dialogact_topics = set(dialog['utterances'][-1]['annotations']['cobot_dialogact']['topics'])
            sensitive_dialogacts_detected = any([(t in self.sensitive_dialogacts and "?" in reply)
                                                 for t in cobot_dialogacts])

            blist_topics_detected = dialog['utterances'][-1]['annotations']['blacklisted_words']['restricted_topics']

            movie_cobot_dialogacts = {
                "Entertainment_Movies", "Sports", "Entertainment_Music", "Entertainment_General",
                "Phatic"
            }
            movie_cobot_topics = {
                "Movies_TV", "Celebrities", "Art_Event", "Entertainment",
                "Fashion", "Games", "Music", "Sports"
            }
            books_cobot_dialogacts = {
                "Entertainment_General", "Entertainment_Books"
            }
            books_cobot_topics = {
                "Entertainment", "Literature"
            }
            about_movies = (movie_cobot_dialogacts & cobot_dialogact_topics) | (movie_cobot_topics & cobot_topics)
            about_music = ("Entertainment_Music" in cobot_dialogact_topics) | ("Music" in cobot_topics)
            about_books = (books_cobot_dialogacts & cobot_dialogact_topics) | (books_cobot_topics & cobot_topics)

            prev_user_uttr_hyp = dialog["utterances"][-3]["hypotheses"] if len(dialog["utterances"]) >= 3 else []
            prev_bot_uttr = dialog["utterances"][-2] if len(dialog["utterances"]) >= 2 else {}

            weather_city_slot_requested = any([
                hyp.get("weather_forecast_interaction_city_slot_requested", False)
                for hyp in prev_user_uttr_hyp if hyp["skill_name"] == "weather_skill"])

            about_weather = dialog['utterances'][-1]['annotations']['intent_catcher'].get(
                "weather_forecast_intent", {}).get("detected", False) or (prev_bot_uttr.get(
                    "active_skill", "") == "weather_skill" and weather_city_slot_requested)

            if "/new_persona" in dialog['utterances'][-1]['text']:
                # process /new_persona command
                skills_for_uttr.append("personality_catcher")  # TODO: rm crutch of personality_catcher
            elif intent_detected:
                # process intent with corresponding IntentResponder
                skills_for_uttr.append("intent_responder")
            elif blist_topics_detected or (sensitive_topics_detected and sensitive_dialogacts_detected):
                # process user utterance with sensitive content
                skills_for_uttr.append("program_y_dangerous")
                skills_for_uttr.append("cobotqa")
            else:
                # process regular utterances
                skills_for_uttr.append("program_y")
                skills_for_uttr.append("cobotqa")
                skills_for_uttr.append("alice")
                skills_for_uttr.append("christmas_new_year_skill")
                skills_for_uttr.append("personal_info_skill")

                if len(dialog['utterances']) > 7:
                    skills_for_uttr.append("tfidf_retrieval")
                    skills_for_uttr.append("convert_reddit")

                # thematic skills
                if about_movies:
                    skills_for_uttr.append("movie_skill")

                if about_music and len(dialog["utterances"]) > 2:
                    skills_for_uttr.append("music_tfidf_retrieval")

                if about_books:
                    skills_for_uttr.append("book_skill")

                if about_weather:
                    skills_for_uttr.append("weather_skill")

                for hyp in prev_user_uttr_hyp:
                    # here we just forcibly add skills which return `can_continue` and it's not `no`
                    if hyp.get("can_continue", CAN_NOT_CONTINUE) in {CAN_CONTINUE, MUST_CONTINUE}:
                        skills_for_uttr.append(hyp["skill_name"])

                if len(dialog['utterances']) > 1:
                    # Use only misheard asr skill if asr is not confident and skip it for greeting
                    if dialog['utterances'][-1]['annotations']['asr']['asr_confidence'] == 'very_low':
                        skills_for_uttr = ["misheard_asr"]

            # always add dummy_skill
            skills_for_uttr.append("dummy_skill")

            skills_for_uttr = list(set(skills_for_uttr))
            skill_names.append(skills_for_uttr)

        return skill_names


selector = RuleBasedSelector()


@app.route("/selected_skills", methods=['POST'])
def respond():
    st_time = time.time()
    states_batch = request.json["states_batch"]
    skill_names = selector(states_batch)
    total_time = time.time() - st_time
    logger.info(f'rule_based_selector exec time: {total_time:.3f}s')
    return jsonify(skill_names)


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=3000)
