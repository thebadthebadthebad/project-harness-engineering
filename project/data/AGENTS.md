# AGENTS

이 규칙은 Project의 공식 `data/`에 적용된다. Task 내부 데이터에는 적용되지 않는다.

- 데이터는 `data/<data-name>/` 단위로 관리한다.
- 원본 데이터가 있으면 `data/<data-name>/raw/`에 저장하고 수정하거나 덮어쓰지 않는다.
- 새 데이터셋을 공식 반영할 때 `data/<data-name>/README.md`를 작성한다.
- README에는 데이터 설명, 출처와 사용 권한, 디렉터리 구성, 생성·변환 방법, 사용 시 유의사항을 기록한다.
- 파생 데이터는 어떤 원본과 과정에서 생성됐는지 README에서 추적할 수 있어야 한다.
- Task 데이터는 검토와 Promotion 없이 공식 `data/`로 복사하지 않는다.
