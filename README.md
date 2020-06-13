# aws-lambda-getSupportPlans

## Business 요구사항
- Consolidated billing시, 각 Linked Accout 들의 Business/Enterprise Support 비용은 Payer Accout에 통합 청구되며(**Premium Support**), Payer 관리 입장에서는 각 어카운트별로 사용량에 비례해서 Support 비용을 각 Linked Account에 배분해야 함
- *(Basic/Developer 등급의 비용은 Payer 계정에 통합청구되지 않으므로 관리 이슈 없음)*
- Enterprise 혹은 Business 를 매월 1일~말일까지 꾸준히 유지하는 경우는 큰 이슈가 없으나, 월 중간에 (예, 15일) 변경하였을 때는, 해당 기간 만큼의 Usage비용에 비례해서 배분해야 하는 요구사항이 있음
- AWS Support Plan 변경 이력은 CloudTrail에도 남지 않으며, CUR(**Cost and Usage Report**)에도 기록이 남지 않아서 월 중간에 가입/탈퇴/등급 변경이 이루어졌을때, 추적이 불가함 *(AWS Support Case를 열어서 Support Plan 변경 이력을 확인하고 있음, (2020-06-13 현재)*

## 기술적 요구사항
- IAM Policy는 describe_support_level을 제공하고 있으나, API는 아직까지 제공하지 않고 있으며, ETA도 불명확한 상태임 (AWS문의 후 답변, [CASE 7086941771])
- describe_severity_levels API의 등급에 따라서 Support Plan 확인이 가능하나, 해당 API는 Business/Enterprise 등급의 Account만 호출 가능, Basic/Developer 등급은 추가개발 필요 **TBD**, 현재는 unknown으로 등록 
- AWS SSO에서 확인 가능한 Linked Accounts들의 access_key_id, secret_access_key, session_token 은 최대 12시간까지만 연장가능해서 정기 배치작업으로 활용 불편, 심지어 AWS SSO는 API제공하지 않음
- 각 Linked Account에 Role 만들고 Assume하는 것이 보안적으로도 가장 좋으나, 고객사 계정이라 함부로 Role 생성 불가
- CMP에 데이터 수집을 위해 ReadOnly 권한으로 공유한 IAM계정 사용
- Lambda활용 및 CloudWatchEvent를 통해서 일과시간은 1시간간격 그리고 매일 마지막 23:45분(KST 기준)에 최종 Support Plan 기록
- Credential 및 DB Access기록은 S3에 기록되며 암호화, Block from Internet 요구사항 만족
- History 조회를 위한 RDS endpoint는 read endpoit 만을 사용자에게 제공

## 설정 순서
- 1 각 계정에 IAM생성
    ReadOnlyAccess(기존Policy), SupportReadOnly(새로생성)권한 Attach
- 2 Lambda실행을 위한 Role 생성
    S3 Access, Support Access, Lambda 실행 권한
- 3 Lambda 생성 시 1번의 Role Assign하고 event handler는 본 repo의 zip 파일을 받아서 업로드
- 4 CloudWatch Event에서 Rule 등록 (*cron(45 23,0,1,2,3,4,5,6,7,8,9,14 \* \* \? \*)*)
    (일과시간 - 1시간마다 확인, 8:45 ~ 18:45 KST, 그리고 23:45 KST에 마지막으로 한번)
- 5 rds 접속 후 이력 확인

## RDS SQL 쿼리
### 어카운트별, 일자별 Support Plan 이력 확인하기
- 두번째 쿼리는 특정 어카운트의 날짜별 이력 확인

    mysql> select distinct account_id, date_format(date_add(date_time, interval 9 hour), '%Y-%m-%d') as DATE_KST, support_level from support_level_history order by account_id, DATE_KST;
    mysql> select distinct account_id, date_format(date_add(date_time, interval 9 hour), '%Y-%m-%d') as DATE_KST, support_level from support_level_history where account_id = '000000000000' order by account_id, DATE_KST;
    mysql>

### 변경 여부 확인
- 다음 쿼리로 조회되는 건은 Support Plan의 변경이 있었던 날임

    mysql> select account_id, DATE_KST, count(distinct support_level) as count from (select account_id, date_format(date_add(date_time, interval 9 hour), '%Y-%m-%d') as DATE_KST, support_level from support_level_history) as data group by 1,2 having count > 1;
    mysql>
    
