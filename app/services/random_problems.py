import random
import logging
import requests

logger = logging.getLogger(__name__)

def get_unsolved_problems(username, count=30):
    url = "https://solved.ac/api/v3/search/problem"

    querystring = {
        "query": f"lang:ko lang:en -solved_by:{username} -tier:r -tier:d",
        "direction": "asc",
        "sort": "random",
        "page": 1,
        "count": count
    }

    headers = {
        "x-solvedac-language": "ko",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()

        data = response.json()
        problem_ids = [item["problemId"] for item in data.get("items", [])]

        return problem_ids
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching problems from solved.ac: {str(e)}")
        raise Exception(f"Failed to fetch problems from solved.ac: {str(e)}")


def generate_random_problems(count=4, username=None, min_problem_id=1000, max_problem_id=100000):
    """
    username이 제공되면 해당 사용자가 풀지 않은 문제 중에서 랜덤 선택
    그렇지 않으면 주어진 범위 내에서 랜덤 선택
    """
    try:
        if username:
            # solved.ac API를 통해 사용자가 풀지 않은 문제 가져오기
            available_problems = get_unsolved_problems(username, count=100)

            # 충분한 문제가 없을 경우 처리
            if len(available_problems) < count:
                logger.warning(
                    f"Not enough unsolved problems for user {username}. Available: {len(available_problems)}, Requested: {count}")
                if not available_problems:
                    # 대체 로직: 범위 내에서 랜덤 선택
                    return random.sample(range(min_problem_id, max_problem_id), count)

            # 요청된 개수만큼 랜덤하게 선택
            return random.sample(available_problems, min(count, len(available_problems)))
        else:
            # 기존 방식: 지정된 범위 내에서 랜덤 선택
            return random.sample(range(min_problem_id, max_problem_id), count)
    except Exception as e:
        logger.error(f"Error generating random problems: {str(e)}")
        raise
