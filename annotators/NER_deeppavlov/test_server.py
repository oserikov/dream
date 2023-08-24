import requests


def main():
    url = "http://0.0.0.0:8021/ner"

    request_data = {
        "last_utterances": [
            ["я видела ивана в москве"],
            ["Я видела Ивана в Москве"],
            ["i have heard about justin. he is in sahara desert"],
            ["I have heard about Justin. He is in Sahara Desert"],
            ["can john smith move forward for 15 meters, then for fifteen meters, and get back to las vegas then"],
            ["я бы проехала на 30 метров вперед, а потом повернула на сорок пять градусов по часовой стрелке"],
            [""],
        ]
    }

    gold_results = [
        [[]],
        [[]],
        [
            [
                {"start_pos": 4, "end_pos": 5, "type": "PER", "text": "justin", "confidence": 1},
                {"start_pos": 9, "end_pos": 11, "type": "LOC", "text": "sahara desert", "confidence": 1},
            ]
        ],
        [
            [
                {"start_pos": 4, "end_pos": 5, "type": "PER", "text": "Justin", "confidence": 1},
                {"start_pos": 9, "end_pos": 11, "type": "LOC", "text": "Sahara Desert", "confidence": 1},
            ]
        ],
        [
            [
                {"start_pos": 1, "end_pos": 3, "type": "PER", "text": "john smith", "confidence": 1},
                {"start_pos": 6, "end_pos": 8, "type": "QUANTITY", "text": "15 meters", "confidence": 1},
                {"start_pos": 11, "end_pos": 13, "type": "QUANTITY", "text": "fifteen meters", "confidence": 1},
                {"start_pos": 18, "end_pos": 20, "type": "LOC", "text": "las vegas", "confidence": 1},
            ]
        ],
        [[]],
        [[]],
    ]

    result = requests.post(url, json=request_data).json()
    assert result == gold_results, print(result)
    print("Success")


if __name__ == "__main__":
    main()
