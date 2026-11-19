# Briefing Board: Dataverse version of the data loader

The Briefing Board canvas app (`canvas-board/`) reads everything through one behavior user-defined function in
`App.Formulas`. It first ships with mock data. When the Dataverse tables are added to the app in Studio, replace the
mock body with the version below. Screens don't change, because both versions fill the same three collections with the
same field names and types.

> The function is named `LoadBriefings()` and not `LoadData()`, because `LoadData` is a built-in Power Fx function
> (offline storage). Defining a UDF with that name compiles only with a "shadows the built-in function" warning.

## 1. Add the data sources

In Power Apps Studio: **Data** > **Add data** > Dataverse, then add these three tables from the
`BriefingNoteGenerator` solution:

| Display name (used in formulas) | Logical name |
|---|---|
| Briefing Requests | `brn_request` |
| Source Documents | `brn_sourcedocument` |
| Briefing Activities | `brn_activity` |

The app only reads them, so users need the read privileges from the existing roles (Briefing Requester, Briefing
Reviewer or Briefing Admin). A requester has Basic (user-level) read on requests and source documents, so they only see
their own requests. Reviewers and admins see everything.

## 2. Replace the body of `LoadBriefings()`

In `App.Formulas`, replace everything from `LoadBriefings(): Void = {` to the closing `};` with the code below.
Leave the helper functions (`LaneOf`, `IsOverdue`, `StatusFg`, and the others) as they are.

The formula uses Dataverse **logical** column names (`brn_status`, `brn_duedate`, and so on). Power Fx accepts them,
and they avoid the ambiguity between the custom **Status** column (`brn_status`) and the built-in **Status**
(`statecode`) column, which both have the display name "Status".

```powerfx
LoadBriefings(): Void = {
    ClearCollect(
        colRequests,
        AddColumns(
            ForAll(
                'Briefing Requests',
                {
                    Id: ThisRecord.brn_requestid,
                    Number: ThisRecord.brn_requestnumber,
                    Subject: ThisRecord.brn_name,
                    Status: Text(ThisRecord.brn_status),
                    Template: ThisRecord.brn_templateid.brn_name,
                    Profile: ThisRecord.brn_profileid.brn_name,
                    Requester: ThisRecord.brn_requestername,
                    Recipient: ThisRecord.brn_recipientname,
                    RecipientTitle: ThisRecord.brn_recipienttitle,
                    DueDate: ThisRecord.brn_duedate,
                    Priority: Text(ThisRecord.brn_priority),
                    Classification: Text(ThisRecord.brn_classification),
                    Language: Text(ThisRecord.brn_language),
                    KeyMessage: ThisRecord.brn_keymessage,
                    NoteTitle: ThisRecord.brn_notetitle,
                    SectionsJson: ThisRecord.brn_draftsections,
                    Verification: ThisRecord.brn_verificationnotes,
                    Confidence: Text(ThisRecord.brn_confidence),
                    Questions: ThisRecord.brn_clarificationquestions,
                    DraftPdf: ThisRecord.brn_draftpdfurl,
                    FinalPdf: ThisRecord.brn_finalpdfurl,
                    Folder: ThisRecord.brn_sharepointfolderurl,
                    Reviewer: ThisRecord.brn_revieweremail,
                    LastError: ThisRecord.brn_lasterror,
                    WordCount: Coalesce(ThisRecord.brn_wordcount, 0),
                    Version: Coalesce(ThisRecord.brn_draftversion, 0),
                    SubmittedOn: ThisRecord.brn_submittedon,
                    DraftedOn: ThisRecord.brn_draftedon,
                    DeliveredOn: ThisRecord.brn_deliveredon,
                    CreatedOn: ThisRecord.createdon
                }
            ),
            Lane, LaneOf(Status)
        )
    );
    ClearCollect(
        colSources,
        ForAll(
            'Source Documents',
            {
                RequestId: ThisRecord.brn_requestid.brn_requestid,
                Label: ThisRecord.brn_sourcelabel,
                FileName: ThisRecord.brn_name,
                DocType: Text(ThisRecord.brn_documenttype),
                Characters: Coalesce(ThisRecord.brn_charactercount, 0),
                Summary: ThisRecord.brn_summary
            }
        )
    );
    ClearCollect(
        colActivities,
        ForAll(
            'Briefing Activities',
            {
                RequestId: ThisRecord.brn_requestid.brn_requestid,
                Title: ThisRecord.brn_name,
                Actor: Text(ThisRecord.brn_actor),
                ActivityType: Text(ThisRecord.brn_activitytype),
                Details: ThisRecord.brn_details,
                CreatedOn: ThisRecord.createdon
            }
        )
    );
    Set(varUpdatedAt, Now())
};
```

## 3. Collection shapes (identical in the mock and Dataverse versions)

| Collection | Field | Type | Dataverse source |
|---|---|---|---|
| colRequests | Id | GUID | `brn_requestid` |
| | Number | Text | `brn_requestnumber` (BN-00001) |
| | Subject | Text | `brn_name` |
| | Status | Text | `Text(brn_status)`: Draft, Submitted, Drafting, Needs Info, Info Provided, In Review, Revision Requested, Approved, Delivered, Cancelled, Needs Attention |
| | Lane | Text | `LaneOf(Status)`: In progress, Needs info, In review, Approved, Delivered, Cancelled |
| | Template | Text | `brn_templateid.brn_name` |
| | Profile | Text | `brn_profileid.brn_name` |
| | Requester, Recipient, RecipientTitle | Text | `brn_requestername`, `brn_recipientname`, `brn_recipienttitle` |
| | DueDate | Date | `brn_duedate` (date only) |
| | Priority, Classification, Language, Confidence | Text | choice labels |
| | KeyMessage, NoteTitle, Verification, Questions, LastError | Text | `brn_keymessage`, `brn_notetitle`, `brn_verificationnotes`, `brn_clarificationquestions`, `brn_lasterror` |
| | SectionsJson | Text | `brn_draftsections`: JSON array of `{"heading","body"}`; body lines starting with `- ` are bullets |
| | DraftPdf, FinalPdf, Folder | Text (URL) | `brn_draftpdfurl`, `brn_finalpdfurl`, `brn_sharepointfolderurl` |
| | Reviewer | Text | `brn_revieweremail` |
| | WordCount, Version | Number | `brn_wordcount`, `brn_draftversion` |
| | SubmittedOn, DraftedOn, DeliveredOn, CreatedOn | DateTime | `brn_submittedon`, `brn_draftedon`, `brn_deliveredon`, `createdon` |
| colSources | RequestId | GUID | `brn_requestid.brn_requestid` |
| | Label, FileName, DocType, Summary | Text | `brn_sourcelabel`, `brn_name`, `Text(brn_documenttype)`, `brn_summary` |
| | Characters | Number | `brn_charactercount` |
| colActivities | RequestId | GUID | `brn_requestid.brn_requestid` |
| | Title, Actor, ActivityType, Details | Text | `brn_name`, `Text(brn_actor)`, `Text(brn_activitytype)`, `brn_details` |
| | CreatedOn | DateTime | `createdon` |

## 4. Limits and options

- **Row limit.** `ForAll` over a Dataverse table isn't delegable, so each collection holds at most the app's
  data-row limit (500 by default, up to 2,000 in **Settings** > **General** > **Data row limit**). For larger volumes,
  apply a delegable filter first, for example
  `ForAll(Filter('Briefing Requests', createdon >= DateAdd(Today(), -365, TimeUnit.Days)), {...})`, and filter the
  sources and activities by the same date.
- **Refresh.** The Refresh button on each screen calls `LoadBriefings()` again. If Studio caches the tables, add
  `Refresh('Briefing Requests'); Refresh('Source Documents'); Refresh('Briefing Activities');` at the top of the
  function body.
- **Blank lookups.** A request without a template or profile gives a blank `Template` or `Profile`. The List screen's
  template filter shows blank templates only under **All templates**.
- **Read-only.** The app never calls `Patch`, `Remove` or `SubmitForm`. Changes are made in Briefing Studio, the
  Briefing Assistant or the Briefing Notes Hub.
