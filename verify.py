import requests
import json

print('--- TEST 1: Base Model (No Graph, No RUD) ---')
p1 = {'features': {'income_mean': 0.3, 'income_cv': 0.2, 'utility_rate': 0.3, 'dti_final': 0.6, 'employment_status': 0, 'shock_total': 0}}
r1 = requests.post('http://127.0.0.1:8000/score', json=p1).json()
print(f'Score: {r1.get("score")}, Graph Boost: {r1.get("graph_boost")}, RUD Boost: {r1.get("rud_boost")}')

print('\n--- TEST 2: Knowledge Graph (user_id 10) ---')
p2 = {**p1, 'user_id': 10}
r2 = requests.post('http://127.0.0.1:8000/score', json=p2).json()
print(f'Score: {r2.get("score")}, Graph Boost: {r2.get("graph_boost")}, Employer: {r2.get("graph_features", {}).get("employer_name")}')

print('\n--- TEST 3: RUD Boost (+5 points) ---')
p3 = {**p2, 'prior_loan': {'repaid': True, 'during_shock': True}}
r3 = requests.post('http://127.0.0.1:8000/score', json=p3).json()
print(f'Score: {r3.get("score")}, RUD Boost: {r3.get("rud_boost")}, Notes: {r3.get("improvement_notes")[:50]}...')

print('\n--- TEST 4: ILF Lie Detector ---')
p4_good = {'latencies': [2.5, 3.0, 2.0], 'answers': ['Agree', 'Agree', 'Disagree']}
r4_good = requests.post('http://127.0.0.1:8000/ilf-score', json=p4_good).json()
print(f'Good Timing -> Reliability Score: {r4_good.get("reliability_score")}')

p4_bad = {'latencies': [0.2, 0.3, 0.1], 'answers': ['Agree', 'Agree', 'Disagree']}
r4_bad = requests.post('http://127.0.0.1:8000/ilf-score', json=p4_bad).json()
print(f'Speed Clicking -> Reliability Score: {r4_bad.get("reliability_score")}')
