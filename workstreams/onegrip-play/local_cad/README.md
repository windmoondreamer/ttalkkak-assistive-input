# OneGrip Play local-first CAD

이 디렉터리는 Onshape와 독립된 로컬 CAD 작업의 경계를 정의한다.

- `reference/`: immutable upstream geometry의 위치와 사용 규칙
- `manifests/`: 해시, 크기, 수정 시각, BBox, solid/component 검증 결과
- 향후 `middle/`, `thumb/`, `integration/`, `output/`: build123d source와 generated output

정책:

1. upstream STEP/STP는 원본 그대로 보존한다.
2. STL은 mesh sanity/reference 또는 제조 출력으로만 사용한다.
3. 신규 형상은 build123d Python source에서 생성한다.
4. baseline STEP과 generated STEP/STL을 같은 파일에 덮어쓰지 않는다.
5. 이 디렉터리의 작업은 Onshape API, browser automation, CAD write를 요구하지 않는다.

현재 MIDDLE shell docking은 JaD/JfD shell STEP 부재로 STOP 상태다. 상세 판정은
`docs/44_local_middle_shell_docking.md`를 따른다.

