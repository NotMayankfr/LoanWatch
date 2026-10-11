/*------------------------------------------------------------------------------
  Program     : loanwatch_recon.sas
  Environment : SAS OnDemand for Academics (SAS Studio 9.4M8)
  Input       : sas_extract_2017.csv (2017 vintage clean loan extract)
  Output      : sas_recon_output_2017.csv
  Purpose     : Independently compute grade-level counts, principal sums, WAC,
                30+ DPD rates, and severe delinquency (proxy) rates for
                tri-system reconciliation against PySpark and PostgreSQL.
------------------------------------------------------------------------------*/

options validvarname=v7 nodate nonumber;

%let base_dir = /home/&sysuserid/loanwatch;
%let in_csv   = &base_dir/sas_extract_2017.csv;
%let out_csv  = &base_dir/sas_recon_output_2017.csv;

/* 1. Import 2017 clean extract using guessingrows=max so SAS scans the entire
      file before assigning string lengths and numeric formats. */
proc import datafile="&in_csv"
    out=work.loans_2017_raw
    dbms=csv
    replace;
    getnames=yes;
    guessingrows=max;
run;

/* 2. DATA step: derive delinquency flags, weighted coupon numerator,
      and charge-off principal metrics matching SQL view definitions. */
data work.loans_2017_prep;
    set work.loans_2017_raw;

    length dpd_segment $24;

    if loan_status in ('Late (31-120 days)', 'Default') then
        is_delinq_30p = 1;
    else
        is_delinq_30p = 0;

    if loan_status in ('Default', 'Charged Off') then
        is_severe_delinq = 1;
    else
        is_severe_delinq = 0;

    if loan_status = 'Current' or loan_status = 'Fully Paid' or loan_status = 'Issued' then
        dpd_segment = 'PERFORMING';
    else if loan_status in ('In Grace Period', 'Late (16-30 days)') then
        dpd_segment = 'EARLY_DELINQ_1_29';
    else if loan_status = 'Late (31-120 days)' then
        dpd_segment = 'DELINQ_30_120';
    else
        dpd_segment = 'SEVERE_DEFAULT_CO';

    rate_x_funded = int_rate * funded_amnt;

    if loan_status = 'Charged Off' then do;
        gross_chargeoff_principal = max(funded_amnt - coalesce(total_rec_prncp, 0), 0);
        co_recoveries = coalesce(recoveries, 0);
    end;
    else do;
        gross_chargeoff_principal = 0;
        co_recoveries = 0;
    end;
run;

/* 3. Frequency distributions across Grade and Servicing Status */
title "LoanWatch 2017 Cohort: Grade by Servicing Status & Delinquency Flags";
proc freq data=work.loans_2017_prep;
    tables grade * dpd_segment / nocol nopercent;
    tables grade * (is_delinq_30p is_severe_delinq) / nocol nopercent;
run;

/* 4. Summary statistics via PROC MEANS (IEEE-754 double precision) */
title "LoanWatch 2017 Cohort: Grade-Level Exposure & Coupon Summary (PROC MEANS)";
proc means data=work.loans_2017_prep n sum mean std maxdec=4;
    class grade;
    var loan_amnt funded_amnt out_prncp int_rate;
    output out=work.grade_means_out
        n(loan_amnt)=loan_count
        sum(loan_amnt)=sum_loan_amnt
        sum(funded_amnt)=sum_funded_amnt
        sum(out_prncp)=sum_out_prncp
        mean(int_rate)=mean_int_rate_pct;
run;

/* 5. Construct formal reconciliation control table via PROC SQL */
title "LoanWatch 2017 Cohort: Formal Tri-System Control Table";
proc sql;
    create table work.sas_recon_summary as
    select
        grade,
        count(*) as loan_count,
        round(sum(loan_amnt), 0.01) as sum_loan_amnt format=16.2,
        round(sum(funded_amnt), 0.01) as sum_funded_amnt format=16.2,
        round(sum(out_prncp), 0.01) as sum_out_prncp format=16.2,
        round(mean(int_rate), 0.000001) as mean_int_rate_pct format=12.6,
        round(sum(rate_x_funded) / sum(funded_amnt), 0.000001) as wac_int_rate_pct format=12.6,
        sum(is_delinq_30p) as delinq_30p_count,
        sum(is_severe_delinq) as severe_delinq_count,
        round(sum(is_delinq_30p) * 100.0 / count(*), 0.000001) as delinq_30p_rate_pct format=12.6,
        round(sum(is_severe_delinq) * 100.0 / count(*), 0.000001) as severe_delinq_rate_pct format=12.6,
        round(sum(gross_chargeoff_principal), 0.01) as gross_chargeoff_principal format=16.2,
        round(sum(co_recoveries), 0.01) as total_recoveries format=16.2
    from work.loans_2017_prep
    group by grade
    order by grade;
quit;

/* 6. Export control totals for automated comparison with PySpark & PostgreSQL */
proc export data=work.sas_recon_summary
    outfile="&out_csv"
    dbms=csv
    replace;
run;
title;
