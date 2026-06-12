import base64
import requests

mermaid_code = """graph TD
    %% 투명 노드를 이용한 외부 입력점 생성 (상자 없이 화살표만 존재하도록 트릭 사용)
    In_T(( )) 
    In_A(( ))
    In_Aud(( ))

    %% 1. 교사 계층
    T1[T1: 절차-독립]
    T2[T2: 절차-연계]
    T3[T3: 개념-독립]
    T4[T4: 개념-연계]
    
    %% 2. 분석관 계층
    A[분석관 에이전트]
    
    %% 3. 심의관 계층
    Aud[심의관 에이전트]

    %% 시스템 외부 입력 -> 4명의 교사에게 할당
    In_T -.->|"[1]평가문항, [2]현재 루브릭, [3]학생답안(1명분), [4]프롬프트"| T1
    In_T -.->|"[1], [2], [3], [4]"| T2
    In_T -.->|"[1], [2], [3], [4]"| T3
    In_T -.->|"[1], [2], [3], [4]"| T4

    %% 교사 출력 -> 분석관으로 집결
    T1 -->|"[5] 채점결과"| A
    T2 -->|"[5] 채점결과"| A
    T3 -->|"[5] 채점결과"| A
    T4 -->|"[5] 채점결과"| A

    %% 분석관 추가 정보 입력
    In_A -.->|"[6]불일치행렬(5의 취합), [7]16명답안, [8]이전/현재루브릭, [9]성취수준, [10]프롬프트"| A

    %% 분석관 출력 -> 심의관으로 이관
    A ===>|"[11] 루브릭 개정 제안서"| Aud

    %% 심의관 추가 정보 입력
    In_Aud -.->|"[9]성취수준, [12]출제의도, [13]평가가이드, [14]실험이력, [15]프롬프트"| Aud

    %% 심의관 최종 판정 및 피드백 순환 루프
    Aud -.->|"[16] 심의 평결서 (REJECTED: 기각 사유 포함하여 분석관에게 반려)"| A
    Aud ===>|"[16] 심의 평결서 (APPROVED: 새 루브릭[2] 갱신 후 새로운 사이클 시작)"| In_T

    %% 스타일링 (에이전트만 박스로 렌더링하고, 입력점은 완전히 투명하게 처리)
    classDef agent fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    class T1,T2,T3,T4,A,Aud agent;
    
    style In_T fill:none,stroke:none,color:transparent;
    style In_A fill:none,stroke:none,color:transparent;
    style In_Aud fill:none,stroke:none,color:transparent;
"""

# Mermaid Ink uses base64 encoded strings
encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('ascii')
url = f"https://mermaid.ink/img/{encoded}?bgColor=FFFFFF"

response = requests.get(url)
if response.status_code == 200:
    with open('/Users/home/vaults/projects/Rubric/paper/figure_1.png', 'wb') as f:
        f.write(response.content)
    print("Successfully downloaded figure_1.png")
else:
    print(f"Failed to fetch image: {response.status_code} {response.text}")
