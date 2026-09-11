export const ActionEnum = {
  viewed: 'viewed',
  downloaded: 'downloaded',
  edited: 'edited',
  deleted: 'deleted',
} as const;

export const ActionTypeEnum = {
  outreach: 'outreach',
  legal_filing: 'legal_filing',
  media: 'media',
  advocacy: 'advocacy',
  investigation: 'investigation',
  other: 'other',
} as const;

export const AdditionalSourceTypeEnum = {
  lawyer: 'lawyer',
  ngo: 'ngo',
  media: 'media',
  court: 'court',
  government: 'government',
  other: 'other',
} as const;

export const BlankEnum = {
  '': '',
} as const;

export const CaseworkRecordStatusEnum = {
  open: 'open',
  in_progress: 'in_progress',
  done: 'done',
} as const;

export const ConsentStatusEnum = {
  yes: 'yes',
  no: 'no',
  pending: 'pending',
} as const;

export const CurrentStatusEnum = {
  detained: 'detained',
  disappeared: 'disappeared',
  restricted_movement: 'restricted_movement',
  released: 'released',
  deceased: 'deceased',
  unknown: 'unknown',
  stateless: 'stateless',
  rights_restricted: 'rights_restricted',
  ongoing_enforced_disappearance: 'ongoing_enforced_disappearance',
  found_alive: 'found_alive',
  found_dead: 'found_dead',
  case_closed: 'case_closed',
  other: 'other',
} as const;

export const DuplicateCheckEnum = {
  no_duplicate: 'no_duplicate',
  possible_duplicate: 'possible_duplicate',
  existing_case: 'existing_case',
} as const;

export const EvidenceKindEnum = {
  fir: 'fir',
  court_petition_order: 'court_petition_order',
  government_document: 'government_document',
  identity_document: 'identity_document',
  photograph: 'photograph',
  medical_document: 'medical_document',
  interview_transcript: 'interview_transcript',
  media_report: 'media_report',
  ngo_report: 'ngo_report',
  other: 'other',
} as const;

export const EvidenceStatusEnum = {
  verified: 'verified',
  partially_verified: 'partially_verified',
  unverified: 'unverified',
  pending: 'pending',
} as const;

export const GenderEnum = {
  M: 'M',
  F: 'F',
  O: 'O',
  U: 'U',
} as const;

export const IncidentDatePrecisionEnum = {
  exact: 'exact',
  approximate: 'approximate',
  unknown: 'unknown',
} as const;

export const KindEnum = {
  record_created: 'record_created',
  record_updated: 'record_updated',
  status_done: 'status_done',
  record_seen: 'record_seen',
} as const;

export const MediaTypeEnum = {
  photo: 'photo',
  document: 'document',
  video: 'video',
  link: 'link',
} as const;

export const MedicalStatusEnum = {
  unknown: 'unknown',
  healthy: 'healthy',
  health_concerns: 'health_concerns',
  critical: 'critical',
  deceased: 'deceased',
} as const;

export const NullEnum = {
} as const;

export const PrimarySourceTypeEnum = {
  victim_survivor: 'victim_survivor',
  family: 'family',
  witness: 'witness',
  official_document: 'official_document',
} as const;

export const PublicIdentityLevelEnum = {
  full: 'full',
  partial: 'partial',
  anonymous: 'anonymous',
} as const;

export const PublicLocationLevelEnum = {
  province: 'province',
  district: 'district',
  city: 'city',
  do_not_disclose: 'do_not_disclose',
} as const;

export const QcReviewDecisionEnum = {
  approved: 'approved',
  corrections_required: 'corrections_required',
  more_verification_required: 'more_verification_required',
  internal_only: 'internal_only',
  do_not_publish: 'do_not_publish',
} as const;

export const QualityTierEnum = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const RelationshipTypeEnum = {
  parent: 'parent',
  child: 'child',
  sibling: 'sibling',
  spouse: 'spouse',
  other: 'other',
} as const;

export const ResponseTypeEnum = {
  confirmation: 'confirmation',
  denial: 'denial',
  investigation: 'investigation',
  detention_acknowledged: 'detention_acknowledged',
  release_confirmed: 'release_confirmed',
  other: 'other',
} as const;

export const RiskLevelEnum = {
  low: 'low',
  moderate: 'moderate',
  high: 'high',
  critical: 'critical',
  not_assessed: 'not_assessed',
} as const;

export const RoleEnum = {
  family: 'family',
  advocate: 'advocate',
  lawyer: 'lawyer',
  official: 'official',
  journalist: 'journalist',
  reporter: 'reporter',
  other: 'other',
} as const;

export const ScopeEnum = {
  staff: 'staff',
  advocate: 'advocate',
  volunteer: 'volunteer',
} as const;

export const SourceConsistencyEnum = {
  consistent: 'consistent',
  some_differences: 'some_differences',
  major_conflict: 'major_conflict',
  requires_further_verification: 'requires_further_verification',
} as const;

export const SourceTypeEnum = {
  firsthand: 'firsthand',
  secondhand: 'secondhand',
  news: 'news',
  document: 'document',
} as const;

export const TestimonialLocationVisibilityEnum = {
  public_precise: 'public_precise',
  public_region: 'public_region',
  public_country: 'public_country',
  hidden: 'hidden',
} as const;

export const TestimonialSourceVisibilityEnum = {
  public_named: 'public_named',
  public_anonymous: 'public_anonymous',
  hidden: 'hidden',
} as const;

export const TestimonialStatusEnum = {
  draft: 'draft',
  under_review: 'under_review',
  approved: 'approved',
  published: 'published',
  rejected: 'rejected',
  archived: 'archived',
} as const;

export const VerificationLevelEnum = {
  level_1_reported: 'level_1_reported',
  level_2_partially_verified: 'level_2_partially_verified',
  level_3_corroborated: 'level_3_corroborated',
  level_4_documented: 'level_4_documented',
} as const;

export const VerificationStatusEnum = {
  reported: 'reported',
  partially_verified: 'partially_verified',
  corroborated: 'corroborated',
  documented: 'documented',
} as const;

export const VisibilityEnum = {
  public: 'public',
  restricted: 'restricted',
  sensitive: 'sensitive',
} as const;

export const YesNoUnknownEnum = {
  yes: 'yes',
  no: 'no',
  unknown: 'unknown',
} as const;

export const AuditLogsListAction = {
  deleted: 'deleted',
  downloaded: 'downloaded',
  edited: 'edited',
  viewed: 'viewed',
} as const;

export const CaseworkListActionType = {
  advocacy: 'advocacy',
  investigation: 'investigation',
  legal_filing: 'legal_filing',
  media: 'media',
  other: 'other',
  outreach: 'outreach',
} as const;

export const CaseworkListStatus = {
  done: 'done',
  in_progress: 'in_progress',
  open: 'open',
} as const;

export const ContactsListRole = {
  advocate: 'advocate',
  family: 'family',
  journalist: 'journalist',
  lawyer: 'lawyer',
  official: 'official',
  other: 'other',
  reporter: 'reporter',
} as const;

export const MediaListMediaType = {
  document: 'document',
  link: 'link',
  photo: 'photo',
  video: 'video',
} as const;

export const MediaListVisibility = {
  public: 'public',
  restricted: 'restricted',
  sensitive: 'sensitive',
} as const;

export const NotificationsListKind = {
  record_created: 'record_created',
  record_seen: 'record_seen',
  record_updated: 'record_updated',
  status_done: 'status_done',
} as const;

export const PersonsListCurrentStatus = {
  case_closed: 'case_closed',
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  found_alive: 'found_alive',
  found_dead: 'found_dead',
  ongoing_enforced_disappearance: 'ongoing_enforced_disappearance',
  other: 'other',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const PersonsCountriesListCurrentStatus = {
  case_closed: 'case_closed',
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  found_alive: 'found_alive',
  found_dead: 'found_dead',
  ongoing_enforced_disappearance: 'ongoing_enforced_disappearance',
  other: 'other',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsCountriesListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsCountriesListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsCountriesListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const PersonsWatchdogListCurrentStatus = {
  case_closed: 'case_closed',
  deceased: 'deceased',
  detained: 'detained',
  disappeared: 'disappeared',
  found_alive: 'found_alive',
  found_dead: 'found_dead',
  ongoing_enforced_disappearance: 'ongoing_enforced_disappearance',
  other: 'other',
  released: 'released',
  restricted_movement: 'restricted_movement',
  rights_restricted: 'rights_restricted',
  stateless: 'stateless',
  unknown: 'unknown',
} as const;

export const PersonsWatchdogListGender = {
  F: 'F',
  M: 'M',
  O: 'O',
  U: 'U',
} as const;

export const PersonsWatchdogListMedicalStatus = {
  critical: 'critical',
  deceased: 'deceased',
  health_concerns: 'health_concerns',
  healthy: 'healthy',
  unknown: 'unknown',
} as const;

export const PersonsWatchdogListQualityTier = {
  NUMBER_1: 1,
  NUMBER_2: 2,
  NUMBER_3: 3,
} as const;

export const RelationshipsListRelationshipType = {
  child: 'child',
  other: 'other',
  parent: 'parent',
  sibling: 'sibling',
  spouse: 'spouse',
} as const;

export const ReportsListSourceType = {
  document: 'document',
  firsthand: 'firsthand',
  news: 'news',
  secondhand: 'secondhand',
} as const;

export const PatchedReportRequestAdditionalSourceType = {...AdditionalSourceTypeEnum,...BlankEnum,} as const

export const ReportAdditionalSourceType = {...AdditionalSourceTypeEnum,...BlankEnum,} as const

export const ReportRequestAdditionalSourceType = {...AdditionalSourceTypeEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestConsentDocumentation = {...ConsentStatusEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestConsentPublicPublication = {...ConsentStatusEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestPhotographPublic = {...ConsentStatusEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestEnteredInWorld = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonDetailConsentDocumentation = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonDetailConsentPublicPublication = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonDetailPhotographPublic = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonDetailEnteredInWorld = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonListConsentDocumentation = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonListConsentPublicPublication = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonListPhotographPublic = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonListEnteredInWorld = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteConsentDocumentation = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteConsentPublicPublication = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWritePhotographPublic = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteEnteredInWorld = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteRequestConsentDocumentation = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteRequestConsentPublicPublication = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteRequestPhotographPublic = {...ConsentStatusEnum,...BlankEnum,} as const

export const PersonWriteRequestEnteredInWorld = {...ConsentStatusEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestDuplicateCheck = {...DuplicateCheckEnum,...BlankEnum,} as const

export const PersonDetailDuplicateCheck = {...DuplicateCheckEnum,...BlankEnum,} as const

export const PersonListDuplicateCheck = {...DuplicateCheckEnum,...BlankEnum,} as const

export const PersonWriteDuplicateCheck = {...DuplicateCheckEnum,...BlankEnum,} as const

export const PersonWriteRequestDuplicateCheck = {...DuplicateCheckEnum,...BlankEnum,} as const

export const MediaEvidenceKind = {...EvidenceKindEnum,...BlankEnum,} as const

export const MediaRequestEvidenceKind = {...EvidenceKindEnum,...BlankEnum,} as const

export const PatchedMediaRequestEvidenceKind = {...EvidenceKindEnum,...BlankEnum,} as const

export const MediaEvidenceStatus = {...EvidenceStatusEnum,...BlankEnum,} as const

export const MediaRequestEvidenceStatus = {...EvidenceStatusEnum,...BlankEnum,} as const

export const PatchedMediaRequestEvidenceStatus = {...EvidenceStatusEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestGender = {...GenderEnum,...BlankEnum,} as const

export const PersonDetailGender = {...GenderEnum,...BlankEnum,} as const

export const PersonListGender = {...GenderEnum,...BlankEnum,} as const

export const PersonWriteGender = {...GenderEnum,...BlankEnum,} as const

export const PersonWriteRequestGender = {...GenderEnum,...BlankEnum,} as const

export const PatchedReportRequestIncidentDatePrecision = {...IncidentDatePrecisionEnum,...BlankEnum,} as const

export const ReportIncidentDatePrecision = {...IncidentDatePrecisionEnum,...BlankEnum,} as const

export const ReportRequestIncidentDatePrecision = {...IncidentDatePrecisionEnum,...BlankEnum,} as const

export const PatchedReportRequestPrimarySourceType = {...PrimarySourceTypeEnum,...BlankEnum,} as const

export const ReportPrimarySourceType = {...PrimarySourceTypeEnum,...BlankEnum,} as const

export const ReportRequestPrimarySourceType = {...PrimarySourceTypeEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestPublicIdentityLevel = {...PublicIdentityLevelEnum,...BlankEnum,} as const

export const PersonDetailPublicIdentityLevel = {...PublicIdentityLevelEnum,...BlankEnum,} as const

export const PersonListPublicIdentityLevel = {...PublicIdentityLevelEnum,...BlankEnum,} as const

export const PersonWritePublicIdentityLevel = {...PublicIdentityLevelEnum,...BlankEnum,} as const

export const PersonWriteRequestPublicIdentityLevel = {...PublicIdentityLevelEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestPublicLocationLevel = {...PublicLocationLevelEnum,...BlankEnum,} as const

export const PersonDetailPublicLocationLevel = {...PublicLocationLevelEnum,...BlankEnum,} as const

export const PersonListPublicLocationLevel = {...PublicLocationLevelEnum,...BlankEnum,} as const

export const PersonWritePublicLocationLevel = {...PublicLocationLevelEnum,...BlankEnum,} as const

export const PersonWriteRequestPublicLocationLevel = {...PublicLocationLevelEnum,...BlankEnum,} as const

export const PatchedReportRequestQcReviewDecision = {...QcReviewDecisionEnum,...BlankEnum,} as const

export const ReportQcReviewDecision = {...QcReviewDecisionEnum,...BlankEnum,} as const

export const ReportRequestQcReviewDecision = {...QcReviewDecisionEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonDetailQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonListQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonWriteQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PersonWriteRequestQualityTier = {...QualityTierEnum,...NullEnum,} as const

export const PatchedReportRequestResponseType = {...ResponseTypeEnum,...BlankEnum,} as const

export const ReportResponseType = {...ResponseTypeEnum,...BlankEnum,} as const

export const ReportRequestResponseType = {...ResponseTypeEnum,...BlankEnum,} as const

export const PatchedReportRequestRiskLevel = {...RiskLevelEnum,...BlankEnum,} as const

export const ReportRiskLevel = {...RiskLevelEnum,...BlankEnum,} as const

export const ReportRequestRiskLevel = {...RiskLevelEnum,...BlankEnum,} as const

export const PatchedReportRequestSourceConsistency = {...SourceConsistencyEnum,...BlankEnum,} as const

export const ReportSourceConsistency = {...SourceConsistencyEnum,...BlankEnum,} as const

export const ReportRequestSourceConsistency = {...SourceConsistencyEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestCurrentStatusVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PatchedPersonWriteRequestPublicVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PatchedReportRequestIncidentVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PatchedReportRequestVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PatchedTestimonialWriteRequestVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonDetailCurrentStatusVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonDetailPublicVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonListCurrentStatusVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonListPublicVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonWriteCurrentStatusVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonWritePublicVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonWriteRequestCurrentStatusVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const PersonWriteRequestPublicVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const ReportIncidentVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const ReportVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const ReportRequestIncidentVerification = {...VerificationLevelEnum,...BlankEnum,} as const

export const ReportRequestVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const TestimonialWriteVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const TestimonialWriteRequestVerificationLevel = {...VerificationLevelEnum,...BlankEnum,} as const

export const PatchedReportRequestDetentionVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const PatchedReportRequestResponseVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const ReportDetentionVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const ReportResponseVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const ReportRequestDetentionVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const ReportRequestResponseVerification = {...VerificationStatusEnum,...BlankEnum,} as const

export const PatchedReportRequestDetentionAlleged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestDetentionAcknowledged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestLegalFirFiled = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestLegalCourtCase = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestLegalCommissionComplaint = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestLegalLawyerInvolved = {...YesNoUnknownEnum,...BlankEnum,} as const

export const PatchedReportRequestOfficialResponse = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportDetentionAlleged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportDetentionAcknowledged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportLegalFirFiled = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportLegalCourtCase = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportLegalCommissionComplaint = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportLegalLawyerInvolved = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportOfficialResponse = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestDetentionAlleged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestDetentionAcknowledged = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestLegalFirFiled = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestLegalCourtCase = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestLegalCommissionComplaint = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestLegalLawyerInvolved = {...YesNoUnknownEnum,...BlankEnum,} as const

export const ReportRequestOfficialResponse = {...YesNoUnknownEnum,...BlankEnum,} as const

/**
 * Generated by orval v7.21.0 🍺
 * Do not edit manually.
 * Testimonies.world API
 * Casework platform for documenting human rights cases. Sensitive endpoints (contacts, sensitive media) require authentication.
 * OpenAPI spec version: 1.0.0
 */
/**
 * * `viewed` - Viewed
* `downloaded` - Downloaded
* `edited` - Edited
* `deleted` - Deleted
 */
export type ActionEnum = typeof ActionEnum[keyof typeof ActionEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `outreach` - Outreach
* `legal_filing` - Legal filing
* `media` - Media engagement
* `advocacy` - Advocacy
* `investigation` - Investigation
* `other` - Other
 */
export type ActionTypeEnum = typeof ActionTypeEnum[keyof typeof ActionTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `lawyer` - Lawyer
* `ngo` - NGO
* `media` - Media
* `court` - Court
* `government` - Government
* `other` - Other
 */
export type AdditionalSourceTypeEnum = typeof AdditionalSourceTypeEnum[keyof typeof AdditionalSourceTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Read-only serializer for the AuditLog API at /api/audit-logs/.

Used by staff-only via AuditLogViewSet (IsAdminUser). The `user`
field is rendered as a primary-key integer for predictability
across the API surface — the frontend resolves the FK to a
username by joining against the user list it already has, rather
than us nesting a User object on every audit row (which would
bloat list payloads and let stale username data leak into the
audit response after a rename).

If a user was deleted (SET_NULL) the FK is null — the frontend
renders '—' for those rows.
 */
export interface AuditLog {
  readonly id: number;
  readonly timestamp: string;
  /** @nullable */
  readonly user: number | null;
  readonly action: ActionEnum;
  readonly target_type: string;
  readonly target_id: number;
  readonly details: string;
  /** @nullable */
  readonly ip_address: string | null;
}

export type BlankEnum = typeof BlankEnum[keyof typeof BlankEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface CaseCategory {
  readonly id: number;
  /** @maxLength 100 */
  name: string;
  description?: string;
}

export type CaseworkRecordSeenByItem = {[key: string]: string};

export interface CaseworkRecord {
  readonly id: number;
  readonly performed_by_name: string;
  readonly seen_by: readonly CaseworkRecordSeenByItem[];
  action_type?: ActionTypeEnum;
  description: string;
  date: string;
  status?: CaseworkRecordStatusEnum;
  next_steps?: string;
  notes?: string;
  readonly created_at: string;
  readonly updated_at: string;
  /** @nullable */
  readonly performed_by: number | null;
  persons?: number[];
}

export interface CaseworkRecordRequest {
  action_type?: ActionTypeEnum;
  /** @minLength 1 */
  description: string;
  date: string;
  status?: CaseworkRecordStatusEnum;
  next_steps?: string;
  notes?: string;
  persons?: number[];
}

/**
 * * `open` - Open
* `in_progress` - In progress
* `done` - Done
 */
export type CaseworkRecordStatusEnum = typeof CaseworkRecordStatusEnum[keyof typeof CaseworkRecordStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface CategoryCount {
  name: string;
  count: number;
}

/**
 * * `yes` - Yes
* `no` - No
* `pending` - Pending
 */
export type ConsentStatusEnum = typeof ConsentStatusEnum[keyof typeof ConsentStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Contact {
  readonly id: number;
  /** @maxLength 255 */
  name: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  readonly created_at: string;
  /** @nullable */
  readonly deleted_at: string | null;
  persons?: number[];
}

export interface ContactRequest {
  /**
   * @minLength 1
   * @maxLength 255
   */
  name: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  persons?: number[];
}

export interface CountryCountEntry {
  country: string;
  count: number;
}

/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
* `ongoing_enforced_disappearance` - Ongoing alleged enforced disappearance
* `found_alive` - Found alive
* `found_dead` - Found dead
* `case_closed` - Case closed
* `other` - Other
 */
export type CurrentStatusEnum = typeof CurrentStatusEnum[keyof typeof CurrentStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface DashboardActivityEntry {
  id: number;
  timestamp: string;
  /**
   * Username, or null for anonymous.
   * @nullable
   */
  user: string | null;
  action: string;
  target_type: string;
  target_id: number;
  details: string;
  /** @nullable */
  ip_address: string | null;
}

export interface DashboardCasework {
  id: number;
  action_type: string;
  status: string;
  date: string;
  description: string;
  /** @nullable */
  performed_by_name: string | null;
  person_ids: number[];
}

export interface DashboardPerson {
  id: number;
  name: string;
  country: string;
  current_status: string;
  updated_at: string;
  /** @nullable */
  profile_image_url: string | null;
}

export interface DashboardReport {
  id: number;
  person: number;
  person_name: string;
  date_start: string;
  source_type: string;
  is_private: boolean;
}

/**
 * Person count grouped by current_status (detained, disappeared, released, deceased, etc.). Mirrors /api/persons/statistics/ for consistency with the public stats page.
 */
export type DashboardResponseByStatus = {[key: string]: number};

export interface DashboardResponse {
  scope: ScopeEnum;
  summary: DashboardSummary;
  recent_persons: DashboardPerson[];
  recent_reports: DashboardReport[];
  recent_casework: DashboardCasework[];
  activity: DashboardActivityEntry[];
  /** Person count grouped by current_status (detained, disappeared, released, deceased, etc.). Mirrors /api/persons/statistics/ for consistency with the public stats page. */
  by_status: DashboardResponseByStatus;
}

export interface DashboardSummary {
  /** Published persons count. */
  open_cases: number;
  /** Casework records visible to this user with status in (open, in_progress). */
  my_open_casework: number;
  unread_notifications: number;
  /** Watchdog count: persons needing attention, capped at 50 by the underlying /api/persons/watchdog/ action. */
  stale_cases: number;
}

/**
 * * `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case
 */
export type DuplicateCheckEnum = typeof DuplicateCheckEnum[keyof typeof DuplicateCheckEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `fir` - FIR
* `court_petition_order` - Court petition/order
* `government_document` - Government document
* `identity_document` - Identity document
* `photograph` - Photograph
* `medical_document` - Medical document
* `interview_transcript` - Interview/transcript
* `media_report` - Media report
* `ngo_report` - NGO report
* `other` - Other
 */
export type EvidenceKindEnum = typeof EvidenceKindEnum[keyof typeof EvidenceKindEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `verified` - Verified
* `partially_verified` - Partially verified
* `unverified` - Unverified
* `pending` - Pending
 */
export type EvidenceStatusEnum = typeof EvidenceStatusEnum[keyof typeof EvidenceStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface FamilyRelationship {
  readonly id: number;
  person_a: number;
  person_b: number;
  readonly person_a_name: string;
  readonly person_b_name: string;
  relationship_type: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface FamilyRelationshipRequest {
  person_a: number;
  person_b: number;
  relationship_type: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
export type GenderEnum = typeof GenderEnum[keyof typeof GenderEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `exact` - Exact
* `approximate` - Approximate
* `unknown` - Unknown
 */
export type IncidentDatePrecisionEnum = typeof IncidentDatePrecisionEnum[keyof typeof IncidentDatePrecisionEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `record_created` - New casework record
* `record_updated` - Casework record updated
* `status_done` - Casework marked done
* `record_seen` - A peer opened this record
 */
export type KindEnum = typeof KindEnum[keyof typeof KindEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface MarkAllReadResponse {
  updated: number;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Media {
  readonly id: number;
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: string | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  readonly created_at: string;
  /** Section H: FIR / Court petition / Photograph / etc.

* `fir` - FIR
* `court_petition_order` - Court petition/order
* `government_document` - Government document
* `identity_document` - Identity document
* `photograph` - Photograph
* `medical_document` - Medical document
* `interview_transcript` - Interview/transcript
* `media_report` - Media report
* `ngo_report` - NGO report
* `other` - Other */
  evidence_kind?: typeof MediaEvidenceKind[keyof typeof MediaEvidenceKind] ;
  /**
   * Free-text when evidence_kind = other.
   * @maxLength 255
   */
  evidence_kind_other?: string;
  /** @maxLength 200 */
  evidence_reference_number?: string;
  /** Section H: Verified / Partially / Unverified / Pending.

* `verified` - Verified
* `partially_verified` - Partially verified
* `unverified` - Unverified
* `pending` - Pending */
  evidence_status?: typeof MediaEvidenceStatus[keyof typeof MediaEvidenceStatus] ;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
  /** @nullable */
  readonly uploaded_by: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface MediaRequest {
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: Blob | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  /** Section H: FIR / Court petition / Photograph / etc.

* `fir` - FIR
* `court_petition_order` - Court petition/order
* `government_document` - Government document
* `identity_document` - Identity document
* `photograph` - Photograph
* `medical_document` - Medical document
* `interview_transcript` - Interview/transcript
* `media_report` - Media report
* `ngo_report` - NGO report
* `other` - Other */
  evidence_kind?: typeof MediaRequestEvidenceKind[keyof typeof MediaRequestEvidenceKind] ;
  /**
   * Free-text when evidence_kind = other.
   * @maxLength 255
   */
  evidence_kind_other?: string;
  /** @maxLength 200 */
  evidence_reference_number?: string;
  /** Section H: Verified / Partially / Unverified / Pending.

* `verified` - Verified
* `partially_verified` - Partially verified
* `unverified` - Unverified
* `pending` - Pending */
  evidence_status?: typeof MediaRequestEvidenceStatus[keyof typeof MediaRequestEvidenceStatus] ;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
}

/**
 * * `photo` - Photo
* `document` - Document
* `video` - Video
* `link` - External link
 */
export type MediaTypeEnum = typeof MediaTypeEnum[keyof typeof MediaTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
export type MedicalStatusEnum = typeof MedicalStatusEnum[keyof typeof MedicalStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Notification {
  readonly id: number;
  readonly kind: KindEnum;
  /** @nullable */
  readonly casework: number | null;
  /**
   * The user whose action caused this notification (often ≠ recipient).
   * @nullable
   */
  readonly actor: number | null;
  readonly actor_name: string;
  readonly casework_action_type: string;
  readonly casework_persons: readonly string[];
  readonly is_read: boolean;
  /** @nullable */
  readonly read_at: string | null;
  readonly created_at: string;
}

export type NullEnum = typeof NullEnum[keyof typeof NullEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface PaginatedAuditLogList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: AuditLog[];
}

export interface PaginatedCaseCategoryList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CaseCategory[];
}

export interface PaginatedCaseworkRecordList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CaseworkRecord[];
}

export interface PaginatedContactList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Contact[];
}

export interface PaginatedCountryCountEntryList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: CountryCountEntry[];
}

export interface PaginatedDashboardResponseList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: DashboardResponse[];
}

export interface PaginatedFamilyRelationshipList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: FamilyRelationship[];
}

export interface PaginatedMediaList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Media[];
}

export interface PaginatedNotificationList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Notification[];
}

export interface PaginatedPersonListList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: PersonList[];
}

export interface PaginatedReportList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: Report[];
}

export interface PaginatedTestimonialPublicList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: TestimonialPublic[];
}

export interface PaginatedTestimonialTagList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: TestimonialTag[];
}

export interface PaginatedUserPreferenceList {
  count: number;
  /** @nullable */
  next?: string | null;
  /** @nullable */
  previous?: string | null;
  results: UserPreference[];
}

export interface PatchedCaseworkRecordRequest {
  action_type?: ActionTypeEnum;
  /** @minLength 1 */
  description?: string;
  date?: string;
  status?: CaseworkRecordStatusEnum;
  next_steps?: string;
  notes?: string;
  persons?: number[];
}

export interface PatchedContactRequest {
  /**
   * @minLength 1
   * @maxLength 255
   */
  name?: string;
  role?: RoleEnum;
  /** @maxLength 50 */
  phone?: string;
  /** @maxLength 254 */
  email?: string;
  /** @maxLength 50 */
  signal?: string;
  /** @maxLength 50 */
  whatsapp?: string;
  notes?: string;
  persons?: number[];
}

/**
 * Family-relationship CRUD payload.

Read shape: full row plus denormalised `person_a_name` /
`person_b_name` so the frontend can render the list without
resolving FK IDs separately.

Write shape: accepts `person_a` and `person_b` as FK IDs (DRF
`PrimaryKeyRelatedField` is the default for `IntegerField`-with-FK
in `ModelSerializer`).

Validation (see `validate`):
    - `person_a != person_b` — no self-link.
    - One row per ordered `(person_a, person_b)` pair, regardless
      of type — the model already enforces this via
      `unique_together = ['person_a', 'person_b']` but we drop
      DRF's auto-validator (see `get_unique_together_validators`)
      so the volunteer sees a friendlier message.
    - For undirected types (`sibling`, `spouse`, `other`), the
      reverse-ordered pair is also rejected. `parent` / `child`
      allow either direction (direction carries meaning).
 */
export interface PatchedFamilyRelationshipRequest {
  person_a?: number;
  person_b?: number;
  relationship_type?: RelationshipTypeEnum;
  /** @maxLength 255 */
  notes?: string;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface PatchedMediaRequest {
  /**
   * @nullable
   * @pattern (?:jpg|jpeg|png|gif|webp|heic|tiff|bmp|pdf|mp4|mov|webm)$
   */
  file?: Blob | null;
  /** @maxLength 1000 */
  url?: string;
  media_type?: MediaTypeEnum;
  visibility?: VisibilityEnum;
  /** @maxLength 500 */
  description?: string;
  /** Section H: FIR / Court petition / Photograph / etc.

* `fir` - FIR
* `court_petition_order` - Court petition/order
* `government_document` - Government document
* `identity_document` - Identity document
* `photograph` - Photograph
* `medical_document` - Medical document
* `interview_transcript` - Interview/transcript
* `media_report` - Media report
* `ngo_report` - NGO report
* `other` - Other */
  evidence_kind?: typeof PatchedMediaRequestEvidenceKind[keyof typeof PatchedMediaRequestEvidenceKind] ;
  /**
   * Free-text when evidence_kind = other.
   * @maxLength 255
   */
  evidence_kind_other?: string;
  /** @maxLength 200 */
  evidence_reference_number?: string;
  /** Section H: Verified / Partially / Unverified / Pending.

* `verified` - Verified
* `partially_verified` - Partially verified
* `unverified` - Unverified
* `pending` - Pending */
  evidence_status?: typeof PatchedMediaRequestEvidenceStatus[keyof typeof PatchedMediaRequestEvidenceStatus] ;
  /** @nullable */
  person?: number | null;
  /** @nullable */
  report?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -9223372036854776000
 * @maximum 9223372036854776000
 * @nullable
 */
export type PatchedPersonWriteRequestQualityTier = typeof PatchedPersonWriteRequestQualityTier[keyof typeof PatchedPersonWriteRequestQualityTier]  | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Serializer for creating/updating persons.
 */
export interface PatchedPersonWriteRequest {
  category_ids?: number[];
  /**
   * @minLength 1
   * @maxLength 255
   */
  name?: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /**
   * @minLength 1
   * @maxLength 100
   */
  country?: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PatchedPersonWriteRequestGender[keyof typeof PatchedPersonWriteRequestGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: Blob | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -9223372036854776000
   * @maximum 9223372036854776000
   * @nullable
   */
  quality_tier?: PatchedPersonWriteRequestQualityTier;
  is_published?: boolean;
  /**
   * Date the case file was received by the documentation officer (Section A).
   * @nullable
   */
  case_received_date?: string | null;
  /** Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A). */
  case_source_types?: unknown;
  /**
   * Free-text when "other" is selected above (Section A).
   * @maxLength 255
   */
  case_source_other?: string;
  /** Duplicate-check outcome (Section A).

* `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case */
  duplicate_check?: typeof PatchedPersonWriteRequestDuplicateCheck[keyof typeof PatchedPersonWriteRequestDuplicateCheck] ;
  /**
   * Age at the time of the incident (Section B). Distinct from date_of_birth.
   * @minimum 0
   * @maximum 9223372036854776000
   * @nullable
   */
  age_at_incident?: number | null;
  /**
   * Occupation at time of incident (Section B).
   * @maxLength 255
   */
  occupation?: string;
  /**
   * Person-level administrative district (Section B). Distinct from Report.incident_district.
   * @maxLength 255
   */
  district?: string;
  /**
   * Person-level administrative province (Section B). Distinct from Report.incident_province.
   * @maxLength 255
   */
  province?: string;
  /** Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B). */
  identity_verified_methods?: unknown;
  /** @maxLength 255 */
  identity_verified_other?: string;
  /**
   * Date the current status was confirmed (Section D).
   * @nullable
   */
  current_status_date?: string | null;
  /**
   * Source of the current-status claim (Section D).
   * @maxLength 500
   */
  current_status_source?: string;
  /** Verification level of the current status (Section D).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  current_status_verification?: typeof PatchedPersonWriteRequestCurrentStatusVerification[keyof typeof PatchedPersonWriteRequestCurrentStatusVerification] ;
  /** Consent for documentation — Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_documentation?: typeof PatchedPersonWriteRequestConsentDocumentation[keyof typeof PatchedPersonWriteRequestConsentDocumentation] ;
  /** Consent for public publication (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_public_publication?: typeof PatchedPersonWriteRequestConsentPublicPublication[keyof typeof PatchedPersonWriteRequestConsentPublicPublication] ;
  /** Full / Partial / Anonymous (Section K).

* `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous */
  public_identity_level?: typeof PatchedPersonWriteRequestPublicIdentityLevel[keyof typeof PatchedPersonWriteRequestPublicIdentityLevel] ;
  /** Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  photograph_public?: typeof PatchedPersonWriteRequestPhotographPublic[keyof typeof PatchedPersonWriteRequestPhotographPublic] ;
  /** Province / District / City / Do not disclose (Section K).

* `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose */
  public_location_level?: typeof PatchedPersonWriteRequestPublicLocationLevel[keyof typeof PatchedPersonWriteRequestPublicLocationLevel] ;
  /** Free-text list of items withheld from publication (Section K). */
  information_restricted_from_publication?: string;
  /** Approved-for-publication summary (Section N). */
  public_summary?: string;
  /**
   * Public-facing status text (Section N).
   * @maxLength 255
   */
  public_status_text?: string;
  /** Mirror of Section L for the public-facing display (Section N).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  public_verification_level?: typeof PatchedPersonWriteRequestPublicVerificationLevel[keyof typeof PatchedPersonWriteRequestPublicVerificationLevel] ;
  /** Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  entered_in_world?: typeof PatchedPersonWriteRequestEnteredInWorld[keyof typeof PatchedPersonWriteRequestEnteredInWorld] ;
  /** @nullable */
  entry_date?: string | null;
  second_person_check_completed?: boolean;
  checked_against_original_documentation?: boolean;
  /** @nullable */
  final_date?: string | null;
  /**
   * Documentation officer who received the case (Section A).
   * @nullable
   */
  case_received_by?: number | null;
  /**
   * Set when duplicate_check = existing_case (Section A).
   * @nullable
   */
  duplicate_of?: number | null;
  /** @nullable */
  entered_by?: number | null;
  /** @nullable */
  final_reviewer?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface PatchedReportRequest {
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  /** @minLength 1 */
  narrative?: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  /** Section C case-type checklist — list from {enforced_disappearance, arbitrary_detention, detention, release_following, death_following, other}. */
  case_types?: unknown;
  /** @maxLength 255 */
  case_type_other?: string;
  /**
   * Date of incident / disappearance (Section C, 4-star field).
   * @nullable
   */
  incident_date?: string | null;
  /** Exact / Approximate / Unknown (Section C).

* `exact` - Exact
* `approximate` - Approximate
* `unknown` - Unknown */
  incident_date_precision?: typeof PatchedReportRequestIncidentDatePrecision[keyof typeof PatchedReportRequestIncidentDatePrecision] ;
  /**
   * Last known location of the person (Section C, 4-star field).
   * @maxLength 500
   */
  last_known_location?: string;
  /**
   * Administrative district of the incident (Section C).
   * @maxLength 255
   */
  incident_district?: string;
  /**
   * Administrative province of the incident (Section C).
   * @maxLength 255
   */
  incident_province?: string;
  /**
   * Source of this specific incident information (Section C).
   * @maxLength 500
   */
  incident_information_source?: string;
  /** Verification status of the incident (Section C).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  incident_verification?: typeof PatchedReportRequestIncidentVerification[keyof typeof PatchedReportRequestIncidentVerification] ;
  /** Section F (4-star): Was detention alleged?

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_alleged?: typeof PatchedReportRequestDetentionAlleged[keyof typeof PatchedReportRequestDetentionAlleged] ;
  /**
   * Alleged detention location (Section F).
   * @maxLength 500
   */
  alleged_detention_location?: string;
  /** Was the detention officially acknowledged? (Section F)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_acknowledged?: typeof PatchedReportRequestDetentionAcknowledged[keyof typeof PatchedReportRequestDetentionAcknowledged] ;
  /** Information / evidence about the detention (Section F). */
  detention_information?: string;
  /** Per-detention verification status (Section F).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  detention_verification?: typeof PatchedReportRequestDetentionVerification[keyof typeof PatchedReportRequestDetentionVerification] ;
  /** Primary source type (Section G).

* `victim_survivor` - Victim/survivor
* `family` - Family
* `witness` - Witness
* `official_document` - Official document */
  primary_source_type?: typeof PatchedReportRequestPrimarySourceType[keyof typeof PatchedReportRequestPrimarySourceType] ;
  /** @maxLength 500 */
  primary_source_description?: string;
  /** Additional source type (Section G).

* `lawyer` - Lawyer
* `ngo` - NGO
* `media` - Media
* `court` - Court
* `government` - Government
* `other` - Other */
  additional_source_type?: typeof PatchedReportRequestAdditionalSourceType[keyof typeof PatchedReportRequestAdditionalSourceType] ;
  /** @maxLength 500 */
  additional_source_description?: string;
  /** Consistency between primary and additional sources (Section G).

* `consistent` - Consistent
* `some_differences` - Some differences
* `major_conflict` - Major conflict
* `requires_further_verification` - Requires further verification */
  source_consistency?: typeof PatchedReportRequestSourceConsistency[keyof typeof PatchedReportRequestSourceConsistency] ;
  /** Free-text verification notes (Section G). */
  source_verification_notes?: string;
  /** Was an FIR filed? (Section I, starred on the form)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_fir_filed?: typeof PatchedReportRequestLegalFirFiled[keyof typeof PatchedReportRequestLegalFirFiled] ;
  /** @maxLength 200 */
  fir_number?: string;
  /** @maxLength 255 */
  police_station?: string;
  /** Was a court case / petition filed? (Section I, starred)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_court_case?: typeof PatchedReportRequestLegalCourtCase[keyof typeof PatchedReportRequestLegalCourtCase] ;
  /** @maxLength 255 */
  court_name?: string;
  /** @maxLength 200 */
  case_number?: string;
  legal_commission_complaint?: typeof PatchedReportRequestLegalCommissionComplaint[keyof typeof PatchedReportRequestLegalCommissionComplaint] ;
  legal_lawyer_involved?: typeof PatchedReportRequestLegalLawyerInvolved[keyof typeof PatchedReportRequestLegalLawyerInvolved] ;
  /** Current status of the legal process (Section I). */
  current_legal_status?: string;
  official_response?: typeof PatchedReportRequestOfficialResponse[keyof typeof PatchedReportRequestOfficialResponse] ;
  /** @maxLength 255 */
  responding_authority?: string;
  /** @nullable */
  response_date?: string | null;
  response_type?: typeof PatchedReportRequestResponseType[keyof typeof PatchedReportRequestResponseType] ;
  /** @maxLength 500 */
  response_source_document?: string;
  /** Per-response verification status (Section J).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  response_verification?: typeof PatchedReportRequestResponseVerification[keyof typeof PatchedReportRequestResponseVerification] ;
  /** Case-level verification ladder (Section L).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  verification_level?: typeof PatchedReportRequestVerificationLevel[keyof typeof PatchedReportRequestVerificationLevel] ;
  /** Why this level was assigned (Section L). */
  verification_reason?: string;
  /** Information that remains unverified (Section L). */
  unverified_information_remaining?: string;
  /** INTERNAL — Section M. Never exposed via public API.

* `low` - Low
* `moderate` - Moderate
* `high` - High
* `critical` - Critical
* `not_assessed` - Not assessed */
  risk_level?: typeof PatchedReportRequestRiskLevel[keyof typeof PatchedReportRequestRiskLevel] ;
  /** INTERNAL — Section M checklist. */
  risk_concerns?: unknown;
  /**
   * INTERNAL — free-text when "other" is selected.
   * @maxLength 255
   */
  risk_concerns_other?: string;
  /** INTERNAL — Section M. Stripped from public API always. */
  internal_notes?: string;
  qc_name_checked?: boolean;
  qc_duplicate_check_completed?: boolean;
  qc_date_checked?: boolean;
  qc_location_checked?: boolean;
  qc_status_checked?: boolean;
  qc_sources_recorded?: boolean;
  qc_evidence_checked?: boolean;
  qc_legal_information_checked?: boolean;
  qc_government_response_checked?: boolean;
  qc_allegations_identified?: boolean;
  qc_consent_checked?: boolean;
  qc_sensitive_information_removed?: boolean;
  qc_verification_level_assigned?: boolean;
  /** @nullable */
  qc_review_date?: string | null;
  qc_review_decision?: typeof PatchedReportRequestQcReviewDecision[keyof typeof PatchedReportRequestQcReviewDecision] ;
  person?: number;
  /** @nullable */
  qc_reviewed_by?: number | null;
}

export interface PatchedTestimonialTagRequest {
  /**
   * @minLength 1
   * @maxLength 64
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  name?: string;
  /** @maxLength 255 */
  description?: string;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Create / update shape for any role (Volunteer can create drafts).

Server-controlled fields are read-only and silently dropped on
input (SYSTEM_RULES §5):
  - status + all `*_by` + `*_at` workflow fields: only mutated
    via the transition actions, never via direct PATCH.
  - schema_version + is_exported: server-pinned.
  - created_by / created_at / updated_at: server-pinned.
  - source_encrypted + precise_location_encrypted: never
    serialized. Caller uses `set_source` / `set_precise_location`
    accessors (exposed via dedicated action endpoints when
    permission is held).
 */
export interface PatchedTestimonialWriteRequest {
  /** @maxLength 255 */
  title?: string;
  /**
   * @maxLength 255
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug?: string;
  /**
   * @minLength 1
   * @maxLength 10
   */
  language?: string;
  /** @maxLength 100 */
  country?: string;
  /** @maxLength 255 */
  region?: string;
  /** @nullable */
  incident_date?: string | null;
  incident_types?: unknown;
  summary?: string;
  narrative?: string;
  outcome?: string;
  source_visibility?: TestimonialSourceVisibilityEnum;
  /** @maxLength 255 */
  public_source_label?: string;
  location_visibility?: TestimonialLocationVisibilityEnum;
  /** @maxLength 500 */
  public_location_display?: string;
  family_protected?: boolean;
  contact_protected?: boolean;
  verification_level?: typeof PatchedTestimonialWriteRequestVerificationLevel[keyof typeof PatchedTestimonialWriteRequestVerificationLevel] ;
  /**
   * Underlying Person this testimonial is built from.
   * @nullable
   */
  person?: number | null;
  /**
   * Optional Report-level link (one event, one testimonial).
   * @nullable
   */
  report?: number | null;
  tags?: number[];
}

export interface PatchedUserPreferenceRequest {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

export type PersonDetailFamilyItem = {[key: string]: unknown};

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -9223372036854776000
 * @maximum 9223372036854776000
 * @nullable
 */
export type PersonDetailQualityTier = typeof PersonDetailQualityTier[keyof typeof PersonDetailQualityTier]  | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Full serializer with reports and media for detail views.
 */
export interface PersonDetail {
  readonly id: number;
  readonly categories: readonly CaseCategory[];
  readonly reports: readonly Report[];
  readonly media_files: readonly Media[];
  readonly days_since_last_report: number;
  readonly family: readonly PersonDetailFamilyItem[];
  /** @nullable */
  readonly profile_image_url: string | null;
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonDetailGender[keyof typeof PersonDetailGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -9223372036854776000
   * @maximum 9223372036854776000
   * @nullable
   */
  quality_tier?: PersonDetailQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** External / website case ID (Section A). */
  readonly case_id: string;
  /**
   * Date the case file was received by the documentation officer (Section A).
   * @nullable
   */
  case_received_date?: string | null;
  /** Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A). */
  case_source_types?: unknown;
  /**
   * Free-text when "other" is selected above (Section A).
   * @maxLength 255
   */
  case_source_other?: string;
  /** Duplicate-check outcome (Section A).

* `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case */
  duplicate_check?: typeof PersonDetailDuplicateCheck[keyof typeof PersonDetailDuplicateCheck] ;
  /**
   * Age at the time of the incident (Section B). Distinct from date_of_birth.
   * @minimum 0
   * @maximum 9223372036854776000
   * @nullable
   */
  age_at_incident?: number | null;
  /**
   * Occupation at time of incident (Section B).
   * @maxLength 255
   */
  occupation?: string;
  /**
   * Person-level administrative district (Section B). Distinct from Report.incident_district.
   * @maxLength 255
   */
  district?: string;
  /**
   * Person-level administrative province (Section B). Distinct from Report.incident_province.
   * @maxLength 255
   */
  province?: string;
  /** Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B). */
  identity_verified_methods?: unknown;
  /** @maxLength 255 */
  identity_verified_other?: string;
  /**
   * Date the current status was confirmed (Section D).
   * @nullable
   */
  current_status_date?: string | null;
  /**
   * Source of the current-status claim (Section D).
   * @maxLength 500
   */
  current_status_source?: string;
  /** Verification level of the current status (Section D).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  current_status_verification?: typeof PersonDetailCurrentStatusVerification[keyof typeof PersonDetailCurrentStatusVerification] ;
  /** Consent for documentation — Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_documentation?: typeof PersonDetailConsentDocumentation[keyof typeof PersonDetailConsentDocumentation] ;
  /** Consent for public publication (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_public_publication?: typeof PersonDetailConsentPublicPublication[keyof typeof PersonDetailConsentPublicPublication] ;
  /** Full / Partial / Anonymous (Section K).

* `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous */
  public_identity_level?: typeof PersonDetailPublicIdentityLevel[keyof typeof PersonDetailPublicIdentityLevel] ;
  /** Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  photograph_public?: typeof PersonDetailPhotographPublic[keyof typeof PersonDetailPhotographPublic] ;
  /** Province / District / City / Do not disclose (Section K).

* `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose */
  public_location_level?: typeof PersonDetailPublicLocationLevel[keyof typeof PersonDetailPublicLocationLevel] ;
  /** Free-text list of items withheld from publication (Section K). */
  information_restricted_from_publication?: string;
  /** Approved-for-publication summary (Section N). */
  public_summary?: string;
  /**
   * Public-facing status text (Section N).
   * @maxLength 255
   */
  public_status_text?: string;
  /** Mirror of Section L for the public-facing display (Section N).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  public_verification_level?: typeof PersonDetailPublicVerificationLevel[keyof typeof PersonDetailPublicVerificationLevel] ;
  /** Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  entered_in_world?: typeof PersonDetailEnteredInWorld[keyof typeof PersonDetailEnteredInWorld] ;
  /** @nullable */
  entry_date?: string | null;
  second_person_check_completed?: boolean;
  checked_against_original_documentation?: boolean;
  /** @nullable */
  final_date?: string | null;
  /** @nullable */
  readonly created_by: number | null;
  /**
   * Documentation officer who received the case (Section A).
   * @nullable
   */
  case_received_by?: number | null;
  /**
   * Set when duplicate_check = existing_case (Section A).
   * @nullable
   */
  duplicate_of?: number | null;
  /** @nullable */
  entered_by?: number | null;
  /** @nullable */
  final_reviewer?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -9223372036854776000
 * @maximum 9223372036854776000
 * @nullable
 */
export type PersonListQualityTier = typeof PersonListQualityTier[keyof typeof PersonListQualityTier]  | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Lightweight serializer for list views.
 */
export interface PersonList {
  readonly id: number;
  readonly categories: readonly CaseCategory[];
  readonly report_count: number;
  /** @nullable */
  readonly days_since_last_report: number | null;
  /** @nullable */
  readonly profile_image_url: string | null;
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonListGender[keyof typeof PersonListGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -9223372036854776000
   * @maximum 9223372036854776000
   * @nullable
   */
  quality_tier?: PersonListQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** External / website case ID (Section A). */
  readonly case_id: string;
  /**
   * Date the case file was received by the documentation officer (Section A).
   * @nullable
   */
  case_received_date?: string | null;
  /** Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A). */
  case_source_types?: unknown;
  /**
   * Free-text when "other" is selected above (Section A).
   * @maxLength 255
   */
  case_source_other?: string;
  /** Duplicate-check outcome (Section A).

* `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case */
  duplicate_check?: typeof PersonListDuplicateCheck[keyof typeof PersonListDuplicateCheck] ;
  /**
   * Age at the time of the incident (Section B). Distinct from date_of_birth.
   * @minimum 0
   * @maximum 9223372036854776000
   * @nullable
   */
  age_at_incident?: number | null;
  /**
   * Occupation at time of incident (Section B).
   * @maxLength 255
   */
  occupation?: string;
  /**
   * Person-level administrative district (Section B). Distinct from Report.incident_district.
   * @maxLength 255
   */
  district?: string;
  /**
   * Person-level administrative province (Section B). Distinct from Report.incident_province.
   * @maxLength 255
   */
  province?: string;
  /** Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B). */
  identity_verified_methods?: unknown;
  /** @maxLength 255 */
  identity_verified_other?: string;
  /**
   * Date the current status was confirmed (Section D).
   * @nullable
   */
  current_status_date?: string | null;
  /**
   * Source of the current-status claim (Section D).
   * @maxLength 500
   */
  current_status_source?: string;
  /** Verification level of the current status (Section D).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  current_status_verification?: typeof PersonListCurrentStatusVerification[keyof typeof PersonListCurrentStatusVerification] ;
  /** Consent for documentation — Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_documentation?: typeof PersonListConsentDocumentation[keyof typeof PersonListConsentDocumentation] ;
  /** Consent for public publication (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_public_publication?: typeof PersonListConsentPublicPublication[keyof typeof PersonListConsentPublicPublication] ;
  /** Full / Partial / Anonymous (Section K).

* `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous */
  public_identity_level?: typeof PersonListPublicIdentityLevel[keyof typeof PersonListPublicIdentityLevel] ;
  /** Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  photograph_public?: typeof PersonListPhotographPublic[keyof typeof PersonListPhotographPublic] ;
  /** Province / District / City / Do not disclose (Section K).

* `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose */
  public_location_level?: typeof PersonListPublicLocationLevel[keyof typeof PersonListPublicLocationLevel] ;
  /** Free-text list of items withheld from publication (Section K). */
  information_restricted_from_publication?: string;
  /** Approved-for-publication summary (Section N). */
  public_summary?: string;
  /**
   * Public-facing status text (Section N).
   * @maxLength 255
   */
  public_status_text?: string;
  /** Mirror of Section L for the public-facing display (Section N).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  public_verification_level?: typeof PersonListPublicVerificationLevel[keyof typeof PersonListPublicVerificationLevel] ;
  /** Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  entered_in_world?: typeof PersonListEnteredInWorld[keyof typeof PersonListEnteredInWorld] ;
  /** @nullable */
  entry_date?: string | null;
  second_person_check_completed?: boolean;
  checked_against_original_documentation?: boolean;
  /** @nullable */
  final_date?: string | null;
  /** @nullable */
  readonly created_by: number | null;
  /**
   * Documentation officer who received the case (Section A).
   * @nullable
   */
  case_received_by?: number | null;
  /**
   * Set when duplicate_check = existing_case (Section A).
   * @nullable
   */
  duplicate_of?: number | null;
  /** @nullable */
  entered_by?: number | null;
  /** @nullable */
  final_reviewer?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -9223372036854776000
 * @maximum 9223372036854776000
 * @nullable
 */
export type PersonWriteQualityTier = typeof PersonWriteQualityTier[keyof typeof PersonWriteQualityTier]  | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Serializer for creating/updating persons.
 */
export interface PersonWrite {
  readonly id: number;
  category_ids?: number[];
  /** @maxLength 255 */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /** @maxLength 100 */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonWriteGender[keyof typeof PersonWriteGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: string | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -9223372036854776000
   * @maximum 9223372036854776000
   * @nullable
   */
  quality_tier?: PersonWriteQualityTier;
  is_published?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** External / website case ID (Section A). */
  readonly case_id: string;
  /**
   * Date the case file was received by the documentation officer (Section A).
   * @nullable
   */
  case_received_date?: string | null;
  /** Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A). */
  case_source_types?: unknown;
  /**
   * Free-text when "other" is selected above (Section A).
   * @maxLength 255
   */
  case_source_other?: string;
  /** Duplicate-check outcome (Section A).

* `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case */
  duplicate_check?: typeof PersonWriteDuplicateCheck[keyof typeof PersonWriteDuplicateCheck] ;
  /**
   * Age at the time of the incident (Section B). Distinct from date_of_birth.
   * @minimum 0
   * @maximum 9223372036854776000
   * @nullable
   */
  age_at_incident?: number | null;
  /**
   * Occupation at time of incident (Section B).
   * @maxLength 255
   */
  occupation?: string;
  /**
   * Person-level administrative district (Section B). Distinct from Report.incident_district.
   * @maxLength 255
   */
  district?: string;
  /**
   * Person-level administrative province (Section B). Distinct from Report.incident_province.
   * @maxLength 255
   */
  province?: string;
  /** Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B). */
  identity_verified_methods?: unknown;
  /** @maxLength 255 */
  identity_verified_other?: string;
  /**
   * Date the current status was confirmed (Section D).
   * @nullable
   */
  current_status_date?: string | null;
  /**
   * Source of the current-status claim (Section D).
   * @maxLength 500
   */
  current_status_source?: string;
  /** Verification level of the current status (Section D).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  current_status_verification?: typeof PersonWriteCurrentStatusVerification[keyof typeof PersonWriteCurrentStatusVerification] ;
  /** Consent for documentation — Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_documentation?: typeof PersonWriteConsentDocumentation[keyof typeof PersonWriteConsentDocumentation] ;
  /** Consent for public publication (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_public_publication?: typeof PersonWriteConsentPublicPublication[keyof typeof PersonWriteConsentPublicPublication] ;
  /** Full / Partial / Anonymous (Section K).

* `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous */
  public_identity_level?: typeof PersonWritePublicIdentityLevel[keyof typeof PersonWritePublicIdentityLevel] ;
  /** Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  photograph_public?: typeof PersonWritePhotographPublic[keyof typeof PersonWritePhotographPublic] ;
  /** Province / District / City / Do not disclose (Section K).

* `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose */
  public_location_level?: typeof PersonWritePublicLocationLevel[keyof typeof PersonWritePublicLocationLevel] ;
  /** Free-text list of items withheld from publication (Section K). */
  information_restricted_from_publication?: string;
  /** Approved-for-publication summary (Section N). */
  public_summary?: string;
  /**
   * Public-facing status text (Section N).
   * @maxLength 255
   */
  public_status_text?: string;
  /** Mirror of Section L for the public-facing display (Section N).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  public_verification_level?: typeof PersonWritePublicVerificationLevel[keyof typeof PersonWritePublicVerificationLevel] ;
  /** Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  entered_in_world?: typeof PersonWriteEnteredInWorld[keyof typeof PersonWriteEnteredInWorld] ;
  /** @nullable */
  entry_date?: string | null;
  second_person_check_completed?: boolean;
  checked_against_original_documentation?: boolean;
  /** @nullable */
  final_date?: string | null;
  /** @nullable */
  readonly created_by: number | null;
  /**
   * Documentation officer who received the case (Section A).
   * @nullable
   */
  case_received_by?: number | null;
  /**
   * Set when duplicate_check = existing_case (Section A).
   * @nullable
   */
  duplicate_of?: number | null;
  /** @nullable */
  entered_by?: number | null;
  /** @nullable */
  final_reviewer?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * @minimum -9223372036854776000
 * @maximum 9223372036854776000
 * @nullable
 */
export type PersonWriteRequestQualityTier = typeof PersonWriteRequestQualityTier[keyof typeof PersonWriteRequestQualityTier]  | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Serializer for creating/updating persons.
 */
export interface PersonWriteRequest {
  category_ids?: number[];
  /**
   * @minLength 1
   * @maxLength 255
   */
  name: string;
  /** @maxLength 255 */
  legal_name?: string;
  /** @maxLength 500 */
  aliases?: string;
  /**
   * @minLength 1
   * @maxLength 100
   */
  country: string;
  /** @maxLength 100 */
  ethnicity?: string;
  gender?: typeof PersonWriteRequestGender[keyof typeof PersonWriteRequestGender] ;
  /** @nullable */
  date_of_birth?: string | null;
  current_status?: CurrentStatusEnum;
  medical_status?: MedicalStatusEnum;
  medical_notes?: string;
  /**
   * Country/region level — shown publicly
   * @maxLength 255
   */
  rough_location?: string;
  /**
   * City/address level — private by default
   * @maxLength 500
   */
  precise_location?: string;
  /** @nullable */
  last_known_date?: string | null;
  summary_narrative?: string;
  /** @nullable */
  profile_image?: Blob | null;
  /**
   * Name of source database — e.g. "AAPP", "HRW", "shahit.biz"
   * @maxLength 255
   */
  authoritative_source?: string;
  /**
   * Link to this case in the original database
   * @maxLength 1000
   */
  authoritative_url?: string;
  /**
   * @minimum -9223372036854776000
   * @maximum 9223372036854776000
   * @nullable
   */
  quality_tier?: PersonWriteRequestQualityTier;
  is_published?: boolean;
  /**
   * Date the case file was received by the documentation officer (Section A).
   * @nullable
   */
  case_received_date?: string | null;
  /** Source-of-case checklist — list from {research_interview, family, victim_survivor, lawyer, ngo_cso, media, government_document, other} (Section A). */
  case_source_types?: unknown;
  /**
   * Free-text when "other" is selected above (Section A).
   * @maxLength 255
   */
  case_source_other?: string;
  /** Duplicate-check outcome (Section A).

* `no_duplicate` - No duplicate identified
* `possible_duplicate` - Possible duplicate
* `existing_case` - Existing case */
  duplicate_check?: typeof PersonWriteRequestDuplicateCheck[keyof typeof PersonWriteRequestDuplicateCheck] ;
  /**
   * Age at the time of the incident (Section B). Distinct from date_of_birth.
   * @minimum 0
   * @maximum 9223372036854776000
   * @nullable
   */
  age_at_incident?: number | null;
  /**
   * Occupation at time of incident (Section B).
   * @maxLength 255
   */
  occupation?: string;
  /**
   * Person-level administrative district (Section B). Distinct from Report.incident_district.
   * @maxLength 255
   */
  district?: string;
  /**
   * Person-level administrative province (Section B). Distinct from Report.incident_province.
   * @maxLength 255
   */
  province?: string;
  /** Identity-verification checklist — list from {interview, family, identity_document, court_document, other} (Section B). */
  identity_verified_methods?: unknown;
  /** @maxLength 255 */
  identity_verified_other?: string;
  /**
   * Date the current status was confirmed (Section D).
   * @nullable
   */
  current_status_date?: string | null;
  /**
   * Source of the current-status claim (Section D).
   * @maxLength 500
   */
  current_status_source?: string;
  /** Verification level of the current status (Section D).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  current_status_verification?: typeof PersonWriteRequestCurrentStatusVerification[keyof typeof PersonWriteRequestCurrentStatusVerification] ;
  /** Consent for documentation — Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_documentation?: typeof PersonWriteRequestConsentDocumentation[keyof typeof PersonWriteRequestConsentDocumentation] ;
  /** Consent for public publication (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  consent_public_publication?: typeof PersonWriteRequestConsentPublicPublication[keyof typeof PersonWriteRequestConsentPublicPublication] ;
  /** Full / Partial / Anonymous (Section K).

* `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous */
  public_identity_level?: typeof PersonWriteRequestPublicIdentityLevel[keyof typeof PersonWriteRequestPublicIdentityLevel] ;
  /** Yes / No / Pending (Section K).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  photograph_public?: typeof PersonWriteRequestPhotographPublic[keyof typeof PersonWriteRequestPhotographPublic] ;
  /** Province / District / City / Do not disclose (Section K).

* `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose */
  public_location_level?: typeof PersonWriteRequestPublicLocationLevel[keyof typeof PersonWriteRequestPublicLocationLevel] ;
  /** Free-text list of items withheld from publication (Section K). */
  information_restricted_from_publication?: string;
  /** Approved-for-publication summary (Section N). */
  public_summary?: string;
  /**
   * Public-facing status text (Section N).
   * @maxLength 255
   */
  public_status_text?: string;
  /** Mirror of Section L for the public-facing display (Section N).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  public_verification_level?: typeof PersonWriteRequestPublicVerificationLevel[keyof typeof PersonWriteRequestPublicVerificationLevel] ;
  /** Has the case been entered into Testimonies.World — Yes / No / Pending (Section P).

* `yes` - Yes
* `no` - No
* `pending` - Pending */
  entered_in_world?: typeof PersonWriteRequestEnteredInWorld[keyof typeof PersonWriteRequestEnteredInWorld] ;
  /** @nullable */
  entry_date?: string | null;
  second_person_check_completed?: boolean;
  checked_against_original_documentation?: boolean;
  /** @nullable */
  final_date?: string | null;
  /**
   * Documentation officer who received the case (Section A).
   * @nullable
   */
  case_received_by?: number | null;
  /**
   * Set when duplicate_check = existing_case (Section A).
   * @nullable
   */
  duplicate_of?: number | null;
  /** @nullable */
  entered_by?: number | null;
  /** @nullable */
  final_reviewer?: number | null;
}

/**
 * * `victim_survivor` - Victim/survivor
* `family` - Family
* `witness` - Witness
* `official_document` - Official document
 */
export type PrimarySourceTypeEnum = typeof PrimarySourceTypeEnum[keyof typeof PrimarySourceTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `full` - Full name
* `partial` - Partial name
* `anonymous` - Anonymous
 */
export type PublicIdentityLevelEnum = typeof PublicIdentityLevelEnum[keyof typeof PublicIdentityLevelEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `province` - Province
* `district` - District
* `city` - City / general area
* `do_not_disclose` - Do not disclose
 */
export type PublicLocationLevelEnum = typeof PublicLocationLevelEnum[keyof typeof PublicLocationLevelEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `approved` - Approved
* `corrections_required` - Corrections required
* `more_verification_required` - More verification required
* `internal_only` - Internal only
* `do_not_publish` - Do not publish
 */
export type QcReviewDecisionEnum = typeof QcReviewDecisionEnum[keyof typeof QcReviewDecisionEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 */
export type QualityTierEnum = typeof QualityTierEnum[keyof typeof QualityTierEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface RelatedPersonsResponse {
  results: PersonList[];
}

/**
 * * `parent` - Parent
* `child` - Child
* `sibling` - Sibling
* `spouse` - Spouse
* `other` - Other relative
 */
export type RelationshipTypeEnum = typeof RelationshipTypeEnum[keyof typeof RelationshipTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface Report {
  readonly id: number;
  readonly media_files: readonly Media[];
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  narrative: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  readonly created_at: string;
  readonly updated_at: string;
  /** Section C case-type checklist — list from {enforced_disappearance, arbitrary_detention, detention, release_following, death_following, other}. */
  case_types?: unknown;
  /** @maxLength 255 */
  case_type_other?: string;
  /**
   * Date of incident / disappearance (Section C, 4-star field).
   * @nullable
   */
  incident_date?: string | null;
  /** Exact / Approximate / Unknown (Section C).

* `exact` - Exact
* `approximate` - Approximate
* `unknown` - Unknown */
  incident_date_precision?: typeof ReportIncidentDatePrecision[keyof typeof ReportIncidentDatePrecision] ;
  /**
   * Last known location of the person (Section C, 4-star field).
   * @maxLength 500
   */
  last_known_location?: string;
  /**
   * Administrative district of the incident (Section C).
   * @maxLength 255
   */
  incident_district?: string;
  /**
   * Administrative province of the incident (Section C).
   * @maxLength 255
   */
  incident_province?: string;
  /**
   * Source of this specific incident information (Section C).
   * @maxLength 500
   */
  incident_information_source?: string;
  /** Verification status of the incident (Section C).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  incident_verification?: typeof ReportIncidentVerification[keyof typeof ReportIncidentVerification] ;
  /** Section F (4-star): Was detention alleged?

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_alleged?: typeof ReportDetentionAlleged[keyof typeof ReportDetentionAlleged] ;
  /**
   * Alleged detention location (Section F).
   * @maxLength 500
   */
  alleged_detention_location?: string;
  /** Was the detention officially acknowledged? (Section F)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_acknowledged?: typeof ReportDetentionAcknowledged[keyof typeof ReportDetentionAcknowledged] ;
  /** Information / evidence about the detention (Section F). */
  detention_information?: string;
  /** Per-detention verification status (Section F).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  detention_verification?: typeof ReportDetentionVerification[keyof typeof ReportDetentionVerification] ;
  /** Primary source type (Section G).

* `victim_survivor` - Victim/survivor
* `family` - Family
* `witness` - Witness
* `official_document` - Official document */
  primary_source_type?: typeof ReportPrimarySourceType[keyof typeof ReportPrimarySourceType] ;
  /** @maxLength 500 */
  primary_source_description?: string;
  /** Additional source type (Section G).

* `lawyer` - Lawyer
* `ngo` - NGO
* `media` - Media
* `court` - Court
* `government` - Government
* `other` - Other */
  additional_source_type?: typeof ReportAdditionalSourceType[keyof typeof ReportAdditionalSourceType] ;
  /** @maxLength 500 */
  additional_source_description?: string;
  /** Consistency between primary and additional sources (Section G).

* `consistent` - Consistent
* `some_differences` - Some differences
* `major_conflict` - Major conflict
* `requires_further_verification` - Requires further verification */
  source_consistency?: typeof ReportSourceConsistency[keyof typeof ReportSourceConsistency] ;
  /** Free-text verification notes (Section G). */
  source_verification_notes?: string;
  /** Was an FIR filed? (Section I, starred on the form)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_fir_filed?: typeof ReportLegalFirFiled[keyof typeof ReportLegalFirFiled] ;
  /** @maxLength 200 */
  fir_number?: string;
  /** @maxLength 255 */
  police_station?: string;
  /** Was a court case / petition filed? (Section I, starred)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_court_case?: typeof ReportLegalCourtCase[keyof typeof ReportLegalCourtCase] ;
  /** @maxLength 255 */
  court_name?: string;
  /** @maxLength 200 */
  case_number?: string;
  legal_commission_complaint?: typeof ReportLegalCommissionComplaint[keyof typeof ReportLegalCommissionComplaint] ;
  legal_lawyer_involved?: typeof ReportLegalLawyerInvolved[keyof typeof ReportLegalLawyerInvolved] ;
  /** Current status of the legal process (Section I). */
  current_legal_status?: string;
  official_response?: typeof ReportOfficialResponse[keyof typeof ReportOfficialResponse] ;
  /** @maxLength 255 */
  responding_authority?: string;
  /** @nullable */
  response_date?: string | null;
  response_type?: typeof ReportResponseType[keyof typeof ReportResponseType] ;
  /** @maxLength 500 */
  response_source_document?: string;
  /** Per-response verification status (Section J).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  response_verification?: typeof ReportResponseVerification[keyof typeof ReportResponseVerification] ;
  /** Case-level verification ladder (Section L).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  verification_level?: typeof ReportVerificationLevel[keyof typeof ReportVerificationLevel] ;
  /** Why this level was assigned (Section L). */
  verification_reason?: string;
  /** Information that remains unverified (Section L). */
  unverified_information_remaining?: string;
  /** INTERNAL — Section M. Never exposed via public API.

* `low` - Low
* `moderate` - Moderate
* `high` - High
* `critical` - Critical
* `not_assessed` - Not assessed */
  risk_level?: typeof ReportRiskLevel[keyof typeof ReportRiskLevel] ;
  /** INTERNAL — Section M checklist. */
  risk_concerns?: unknown;
  /**
   * INTERNAL — free-text when "other" is selected.
   * @maxLength 255
   */
  risk_concerns_other?: string;
  /** INTERNAL — Section M. Stripped from public API always. */
  internal_notes?: string;
  qc_name_checked?: boolean;
  qc_duplicate_check_completed?: boolean;
  qc_date_checked?: boolean;
  qc_location_checked?: boolean;
  qc_status_checked?: boolean;
  qc_sources_recorded?: boolean;
  qc_evidence_checked?: boolean;
  qc_legal_information_checked?: boolean;
  qc_government_response_checked?: boolean;
  qc_allegations_identified?: boolean;
  qc_consent_checked?: boolean;
  qc_sensitive_information_removed?: boolean;
  qc_verification_level_assigned?: boolean;
  /** @nullable */
  qc_review_date?: string | null;
  qc_review_decision?: typeof ReportQcReviewDecision[keyof typeof ReportQcReviewDecision] ;
  person: number;
  /** @nullable */
  readonly created_by: number | null;
  /** @nullable */
  qc_reviewed_by?: number | null;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface ReportRequest {
  source_type?: SourceTypeEnum;
  /**
   * Public attribution — e.g. "family member", "BBC report"
   * @maxLength 500
   */
  source_attribution?: string;
  /** @maxLength 255 */
  reporter_name?: string;
  reporter_contact?: string;
  /** @nullable */
  date_start?: string | null;
  /**
   * Leave blank for single-date events
   * @nullable
   */
  date_end?: string | null;
  /** @maxLength 255 */
  rough_location?: string;
  /** @maxLength 500 */
  precise_location?: string;
  /** @minLength 1 */
  narrative: string;
  /** What family/source believes is the reason */
  suspected_reason?: string;
  /** What the state officially charged */
  official_reason?: string;
  /** If true, entire report hidden from public view */
  is_private?: boolean;
  /** Section C case-type checklist — list from {enforced_disappearance, arbitrary_detention, detention, release_following, death_following, other}. */
  case_types?: unknown;
  /** @maxLength 255 */
  case_type_other?: string;
  /**
   * Date of incident / disappearance (Section C, 4-star field).
   * @nullable
   */
  incident_date?: string | null;
  /** Exact / Approximate / Unknown (Section C).

* `exact` - Exact
* `approximate` - Approximate
* `unknown` - Unknown */
  incident_date_precision?: typeof ReportRequestIncidentDatePrecision[keyof typeof ReportRequestIncidentDatePrecision] ;
  /**
   * Last known location of the person (Section C, 4-star field).
   * @maxLength 500
   */
  last_known_location?: string;
  /**
   * Administrative district of the incident (Section C).
   * @maxLength 255
   */
  incident_district?: string;
  /**
   * Administrative province of the incident (Section C).
   * @maxLength 255
   */
  incident_province?: string;
  /**
   * Source of this specific incident information (Section C).
   * @maxLength 500
   */
  incident_information_source?: string;
  /** Verification status of the incident (Section C).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  incident_verification?: typeof ReportRequestIncidentVerification[keyof typeof ReportRequestIncidentVerification] ;
  /** Section F (4-star): Was detention alleged?

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_alleged?: typeof ReportRequestDetentionAlleged[keyof typeof ReportRequestDetentionAlleged] ;
  /**
   * Alleged detention location (Section F).
   * @maxLength 500
   */
  alleged_detention_location?: string;
  /** Was the detention officially acknowledged? (Section F)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  detention_acknowledged?: typeof ReportRequestDetentionAcknowledged[keyof typeof ReportRequestDetentionAcknowledged] ;
  /** Information / evidence about the detention (Section F). */
  detention_information?: string;
  /** Per-detention verification status (Section F).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  detention_verification?: typeof ReportRequestDetentionVerification[keyof typeof ReportRequestDetentionVerification] ;
  /** Primary source type (Section G).

* `victim_survivor` - Victim/survivor
* `family` - Family
* `witness` - Witness
* `official_document` - Official document */
  primary_source_type?: typeof ReportRequestPrimarySourceType[keyof typeof ReportRequestPrimarySourceType] ;
  /** @maxLength 500 */
  primary_source_description?: string;
  /** Additional source type (Section G).

* `lawyer` - Lawyer
* `ngo` - NGO
* `media` - Media
* `court` - Court
* `government` - Government
* `other` - Other */
  additional_source_type?: typeof ReportRequestAdditionalSourceType[keyof typeof ReportRequestAdditionalSourceType] ;
  /** @maxLength 500 */
  additional_source_description?: string;
  /** Consistency between primary and additional sources (Section G).

* `consistent` - Consistent
* `some_differences` - Some differences
* `major_conflict` - Major conflict
* `requires_further_verification` - Requires further verification */
  source_consistency?: typeof ReportRequestSourceConsistency[keyof typeof ReportRequestSourceConsistency] ;
  /** Free-text verification notes (Section G). */
  source_verification_notes?: string;
  /** Was an FIR filed? (Section I, starred on the form)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_fir_filed?: typeof ReportRequestLegalFirFiled[keyof typeof ReportRequestLegalFirFiled] ;
  /** @maxLength 200 */
  fir_number?: string;
  /** @maxLength 255 */
  police_station?: string;
  /** Was a court case / petition filed? (Section I, starred)

* `yes` - Yes
* `no` - No
* `unknown` - Unknown */
  legal_court_case?: typeof ReportRequestLegalCourtCase[keyof typeof ReportRequestLegalCourtCase] ;
  /** @maxLength 255 */
  court_name?: string;
  /** @maxLength 200 */
  case_number?: string;
  legal_commission_complaint?: typeof ReportRequestLegalCommissionComplaint[keyof typeof ReportRequestLegalCommissionComplaint] ;
  legal_lawyer_involved?: typeof ReportRequestLegalLawyerInvolved[keyof typeof ReportRequestLegalLawyerInvolved] ;
  /** Current status of the legal process (Section I). */
  current_legal_status?: string;
  official_response?: typeof ReportRequestOfficialResponse[keyof typeof ReportRequestOfficialResponse] ;
  /** @maxLength 255 */
  responding_authority?: string;
  /** @nullable */
  response_date?: string | null;
  response_type?: typeof ReportRequestResponseType[keyof typeof ReportRequestResponseType] ;
  /** @maxLength 500 */
  response_source_document?: string;
  /** Per-response verification status (Section J).

* `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented */
  response_verification?: typeof ReportRequestResponseVerification[keyof typeof ReportRequestResponseVerification] ;
  /** Case-level verification ladder (Section L).

* `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented */
  verification_level?: typeof ReportRequestVerificationLevel[keyof typeof ReportRequestVerificationLevel] ;
  /** Why this level was assigned (Section L). */
  verification_reason?: string;
  /** Information that remains unverified (Section L). */
  unverified_information_remaining?: string;
  /** INTERNAL — Section M. Never exposed via public API.

* `low` - Low
* `moderate` - Moderate
* `high` - High
* `critical` - Critical
* `not_assessed` - Not assessed */
  risk_level?: typeof ReportRequestRiskLevel[keyof typeof ReportRequestRiskLevel] ;
  /** INTERNAL — Section M checklist. */
  risk_concerns?: unknown;
  /**
   * INTERNAL — free-text when "other" is selected.
   * @maxLength 255
   */
  risk_concerns_other?: string;
  /** INTERNAL — Section M. Stripped from public API always. */
  internal_notes?: string;
  qc_name_checked?: boolean;
  qc_duplicate_check_completed?: boolean;
  qc_date_checked?: boolean;
  qc_location_checked?: boolean;
  qc_status_checked?: boolean;
  qc_sources_recorded?: boolean;
  qc_evidence_checked?: boolean;
  qc_legal_information_checked?: boolean;
  qc_government_response_checked?: boolean;
  qc_allegations_identified?: boolean;
  qc_consent_checked?: boolean;
  qc_sensitive_information_removed?: boolean;
  qc_verification_level_assigned?: boolean;
  /** @nullable */
  qc_review_date?: string | null;
  qc_review_decision?: typeof ReportRequestQcReviewDecision[keyof typeof ReportRequestQcReviewDecision] ;
  person: number;
  /** @nullable */
  qc_reviewed_by?: number | null;
}

/**
 * * `confirmation` - Confirmation
* `denial` - Denial
* `investigation` - Investigation
* `detention_acknowledged` - Detention acknowledged
* `release_confirmed` - Release confirmed
* `other` - Other
 */
export type ResponseTypeEnum = typeof ResponseTypeEnum[keyof typeof ResponseTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `low` - Low
* `moderate` - Moderate
* `high` - High
* `critical` - Critical
* `not_assessed` - Not assessed
 */
export type RiskLevelEnum = typeof RiskLevelEnum[keyof typeof RiskLevelEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `family` - Family member
* `advocate` - Advocate
* `lawyer` - Lawyer
* `official` - Government official
* `journalist` - Journalist
* `reporter` - Reporter/witness
* `other` - Other
 */
export type RoleEnum = typeof RoleEnum[keyof typeof RoleEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `staff` - staff
* `advocate` - advocate
* `volunteer` - volunteer
 */
export type ScopeEnum = typeof ScopeEnum[keyof typeof ScopeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `consistent` - Consistent
* `some_differences` - Some differences
* `major_conflict` - Major conflict
* `requires_further_verification` - Requires further verification
 */
export type SourceConsistencyEnum = typeof SourceConsistencyEnum[keyof typeof SourceConsistencyEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `firsthand` - Firsthand
* `secondhand` - Secondhand
* `news` - News report
* `document` - Document
 */
export type SourceTypeEnum = typeof SourceTypeEnum[keyof typeof SourceTypeEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface StatisticsCountryCount {
  country: string;
  count: number;
}

export type StatisticsResponseByStatus = {[key: string]: number};

export type StatisticsResponseByMedical = {[key: string]: number};

export interface StatisticsResponse {
  total: number;
  by_status: StatisticsResponseByStatus;
  by_country: StatisticsCountryCount[];
  by_category: CategoryCount[];
  by_medical: StatisticsResponseByMedical;
}

/**
 * * `public_precise` - Public — precise
* `public_region` - Public — region only
* `public_country` - Public — country only
* `hidden` - Hidden
 */
export type TestimonialLocationVisibilityEnum = typeof TestimonialLocationVisibilityEnum[keyof typeof TestimonialLocationVisibilityEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Public-facing payload — masks source + location by visibility flags.

Server-side masking is the security boundary (SYSTEM_RULES §10).
The frontend never sees redacted fields in the first place.

The `source_visible` boolean captures whether *any* source
descriptor is shown publicly (public_named / public_anonymous).
Hidden rows surface `null`.
 */
export interface TestimonialPublic {
  readonly id: number;
  /** @pattern ^[-a-zA-Z0-9_]+$ */
  readonly slug: string;
  readonly title: string;
  readonly language: string;
  readonly country: string;
  readonly region: string;
  readonly public_location_display: string;
  /** @nullable */
  readonly incident_date: string | null;
  readonly incident_types: unknown;
  readonly summary: string;
  readonly narrative: string;
  readonly outcome: string;
  readonly verification_level: VerificationLevelEnum;
  readonly source_visible: boolean;
  readonly public_source_label: string;
  readonly family_protected: boolean;
  readonly contact_protected: boolean;
  readonly status: TestimonialStatusEnum;
  /** @nullable */
  readonly published_at: string | null;
  readonly tags: readonly TestimonialTag[];
  readonly translation_group: string;
  readonly linked_person_id: number;
  readonly linked_report_id: number;
  readonly schema_version: number;
}

/**
 * * `public_named` - Public — named
* `public_anonymous` - Public — anonymous
* `hidden` - Hidden
 */
export type TestimonialSourceVisibilityEnum = typeof TestimonialSourceVisibilityEnum[keyof typeof TestimonialSourceVisibilityEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `draft` - Draft
* `under_review` - Under review
* `approved` - Approved
* `published` - Published
* `rejected` - Rejected
* `archived` - Archived
 */
export type TestimonialStatusEnum = typeof TestimonialStatusEnum[keyof typeof TestimonialStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export interface TestimonialTag {
  readonly id: number;
  /**
   * @maxLength 64
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  name: string;
  /** @maxLength 255 */
  description?: string;
}

export interface TestimonialTagRequest {
  /**
   * @minLength 1
   * @maxLength 64
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  name: string;
  /** @maxLength 255 */
  description?: string;
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Create / update shape for any role (Volunteer can create drafts).

Server-controlled fields are read-only and silently dropped on
input (SYSTEM_RULES §5):
  - status + all `*_by` + `*_at` workflow fields: only mutated
    via the transition actions, never via direct PATCH.
  - schema_version + is_exported: server-pinned.
  - created_by / created_at / updated_at: server-pinned.
  - source_encrypted + precise_location_encrypted: never
    serialized. Caller uses `set_source` / `set_precise_location`
    accessors (exposed via dedicated action endpoints when
    permission is held).
 */
export interface TestimonialWrite {
  readonly id: number;
  /** @maxLength 255 */
  title?: string;
  /**
   * @maxLength 255
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug?: string;
  /** @maxLength 10 */
  language?: string;
  /** @maxLength 100 */
  country?: string;
  /** @maxLength 255 */
  region?: string;
  /** @nullable */
  incident_date?: string | null;
  incident_types?: unknown;
  summary?: string;
  narrative?: string;
  outcome?: string;
  source_visibility?: TestimonialSourceVisibilityEnum;
  /** @maxLength 255 */
  public_source_label?: string;
  location_visibility?: TestimonialLocationVisibilityEnum;
  /** @maxLength 500 */
  public_location_display?: string;
  family_protected?: boolean;
  contact_protected?: boolean;
  verification_level?: typeof TestimonialWriteVerificationLevel[keyof typeof TestimonialWriteVerificationLevel] ;
  /**
   * Underlying Person this testimonial is built from.
   * @nullable
   */
  person?: number | null;
  /**
   * Optional Report-level link (one event, one testimonial).
   * @nullable
   */
  report?: number | null;
  tags?: number[];
}

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * Create / update shape for any role (Volunteer can create drafts).

Server-controlled fields are read-only and silently dropped on
input (SYSTEM_RULES §5):
  - status + all `*_by` + `*_at` workflow fields: only mutated
    via the transition actions, never via direct PATCH.
  - schema_version + is_exported: server-pinned.
  - created_by / created_at / updated_at: server-pinned.
  - source_encrypted + precise_location_encrypted: never
    serialized. Caller uses `set_source` / `set_precise_location`
    accessors (exposed via dedicated action endpoints when
    permission is held).
 */
export interface TestimonialWriteRequest {
  /** @maxLength 255 */
  title?: string;
  /**
   * @maxLength 255
   * @pattern ^[-a-zA-Z0-9_]+$
   */
  slug?: string;
  /**
   * @minLength 1
   * @maxLength 10
   */
  language?: string;
  /** @maxLength 100 */
  country?: string;
  /** @maxLength 255 */
  region?: string;
  /** @nullable */
  incident_date?: string | null;
  incident_types?: unknown;
  summary?: string;
  narrative?: string;
  outcome?: string;
  source_visibility?: TestimonialSourceVisibilityEnum;
  /** @maxLength 255 */
  public_source_label?: string;
  location_visibility?: TestimonialLocationVisibilityEnum;
  /** @maxLength 500 */
  public_location_display?: string;
  family_protected?: boolean;
  contact_protected?: boolean;
  verification_level?: typeof TestimonialWriteRequestVerificationLevel[keyof typeof TestimonialWriteRequestVerificationLevel] ;
  /**
   * Underlying Person this testimonial is built from.
   * @nullable
   */
  person?: number | null;
  /**
   * Optional Report-level link (one event, one testimonial).
   * @nullable
   */
  report?: number | null;
  tags?: number[];
}

export interface UnreadCountResponse {
  count: number;
}

export interface UserPreference {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

export interface UserPreferenceRequest {
  /** Receive an email when casework events affect you. */
  notify_email?: boolean;
  /** Show in-app notifications in the bell. */
  notify_inapp?: boolean;
}

/**
 * * `level_1_reported` - Level 1 — Reported
* `level_2_partially_verified` - Level 2 — Partially verified
* `level_3_corroborated` - Level 3 — Corroborated
* `level_4_documented` - Level 4 — Documented
 */
export type VerificationLevelEnum = typeof VerificationLevelEnum[keyof typeof VerificationLevelEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `reported` - Reported
* `partially_verified` - Partially verified
* `corroborated` - Corroborated
* `documented` - Documented
 */
export type VerificationStatusEnum = typeof VerificationStatusEnum[keyof typeof VerificationStatusEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `public` - Public
* `restricted` - Restricted — authenticated users only
* `sensitive` - Sensitive — advocates/admin only
 */
export type VisibilityEnum = typeof VisibilityEnum[keyof typeof VisibilityEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

/**
 * * `yes` - Yes
* `no` - No
* `unknown` - Unknown
 */
export type YesNoUnknownEnum = typeof YesNoUnknownEnum[keyof typeof YesNoUnknownEnum];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type AuditLogsListParams = {
/**
 * * `viewed` - Viewed
* `downloaded` - Downloaded
* `edited` - Edited
* `deleted` - Deleted
 */
action?: AuditLogsListAction;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
target_type?: string;
timestamp_after?: string;
timestamp_before?: string;
user__username?: string;
};

export type AuditLogsListAction = typeof AuditLogsListAction[keyof typeof AuditLogsListAction];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CaseworkListParams = {
/**
 * * `outreach` - Outreach
* `legal_filing` - Legal filing
* `media` - Media engagement
* `advocacy` - Advocacy
* `investigation` - Investigation
* `other` - Other
 */
action_type?: CaseworkListActionType;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
performed_by?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `open` - Open
* `in_progress` - In progress
* `done` - Done
 */
status?: CaseworkListStatus;
};

export type CaseworkListActionType = typeof CaseworkListActionType[keyof typeof CaseworkListActionType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CaseworkListStatus = typeof CaseworkListStatus[keyof typeof CaseworkListStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type CategoriesListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type ContactsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * * `family` - Family member
* `advocate` - Advocate
* `lawyer` - Lawyer
* `official` - Government official
* `journalist` - Journalist
* `reporter` - Reporter/witness
* `other` - Other
 */
role?: ContactsListRole;
/**
 * A search term.
 */
search?: string;
};

export type ContactsListRole = typeof ContactsListRole[keyof typeof ContactsListRole];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type DashboardListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type MediaListParams = {
/**
 * * `photo` - Photo
* `document` - Document
* `video` - Video
* `link` - External link
 */
media_type?: MediaListMediaType;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
report?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `public` - Public
* `restricted` - Restricted — authenticated users only
* `sensitive` - Sensitive — advocates/admin only
 */
visibility?: MediaListVisibility;
};

export type MediaListMediaType = typeof MediaListMediaType[keyof typeof MediaListMediaType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type MediaListVisibility = typeof MediaListVisibility[keyof typeof MediaListVisibility];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type NotificationsListParams = {
is_read?: boolean;
/**
 * * `record_created` - New casework record
* `record_updated` - Casework record updated
* `status_done` - Casework marked done
* `record_seen` - A peer opened this record
 */
kind?: NotificationsListKind;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type NotificationsListKind = typeof NotificationsListKind[keyof typeof NotificationsListKind];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
* `ongoing_enforced_disappearance` - Ongoing alleged enforced disappearance
* `found_alive` - Found alive
* `found_dead` - Found dead
* `case_closed` - Case closed
* `other` - Other
 */
current_status?: PersonsListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsListQualityTier;
/**
 * A search term.
 */
search?: string;
stale?: string;
status?: string;
updated_after?: string;
updated_before?: string;
};

export type PersonsListCurrentStatus = typeof PersonsListCurrentStatus[keyof typeof PersonsListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListGender = typeof PersonsListGender[keyof typeof PersonsListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListMedicalStatus = typeof PersonsListMedicalStatus[keyof typeof PersonsListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsListQualityTier = typeof PersonsListQualityTier[keyof typeof PersonsListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
* `ongoing_enforced_disappearance` - Ongoing alleged enforced disappearance
* `found_alive` - Found alive
* `found_dead` - Found dead
* `case_closed` - Case closed
* `other` - Other
 */
current_status?: PersonsCountriesListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsCountriesListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsCountriesListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsCountriesListQualityTier;
/**
 * A search term.
 */
search?: string;
stale?: string;
status?: string;
updated_after?: string;
updated_before?: string;
};

export type PersonsCountriesListCurrentStatus = typeof PersonsCountriesListCurrentStatus[keyof typeof PersonsCountriesListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListGender = typeof PersonsCountriesListGender[keyof typeof PersonsCountriesListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListMedicalStatus = typeof PersonsCountriesListMedicalStatus[keyof typeof PersonsCountriesListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsCountriesListQualityTier = typeof PersonsCountriesListQualityTier[keyof typeof PersonsCountriesListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListParams = {
category?: number[];
country?: string;
/**
 * * `detained` - Detained
* `disappeared` - Disappeared
* `restricted_movement` - Restricted Movement
* `released` - Released
* `deceased` - Deceased
* `unknown` - Unknown
* `stateless` - Stateless
* `rights_restricted` - Rights Restricted
* `ongoing_enforced_disappearance` - Ongoing alleged enforced disappearance
* `found_alive` - Found alive
* `found_dead` - Found dead
* `case_closed` - Case closed
* `other` - Other
 */
current_status?: PersonsWatchdogListCurrentStatus;
/**
 * * `M` - Male
* `F` - Female
* `O` - Other
* `U` - Unknown
 */
gender?: PersonsWatchdogListGender;
is_published?: boolean;
/**
 * * `unknown` - Unknown
* `healthy` - Healthy
* `health_concerns` - Health Concerns
* `critical` - Critical
* `deceased` - Deceased
 */
medical_status?: PersonsWatchdogListMedicalStatus;
name?: string;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
quality?: number;
/**
 * * `1` - Tier 1 — Strong evidence
* `2` - Tier 2 — Average evidence
* `3` - Tier 3 — Weak evidence
 * @nullable
 */
quality_tier?: PersonsWatchdogListQualityTier;
/**
 * A search term.
 */
search?: string;
stale?: string;
status?: string;
updated_after?: string;
updated_before?: string;
};

export type PersonsWatchdogListCurrentStatus = typeof PersonsWatchdogListCurrentStatus[keyof typeof PersonsWatchdogListCurrentStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListGender = typeof PersonsWatchdogListGender[keyof typeof PersonsWatchdogListGender];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListMedicalStatus = typeof PersonsWatchdogListMedicalStatus[keyof typeof PersonsWatchdogListMedicalStatus];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PersonsWatchdogListQualityTier = typeof PersonsWatchdogListQualityTier[keyof typeof PersonsWatchdogListQualityTier] | null;

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type PreferencesListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type RelationshipsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
/**
 * * `parent` - Parent
* `child` - Child
* `sibling` - Sibling
* `spouse` - Spouse
* `other` - Other relative
 */
relationship_type?: RelationshipsListRelationshipType;
/**
 * A search term.
 */
search?: string;
};

export type RelationshipsListRelationshipType = typeof RelationshipsListRelationshipType[keyof typeof RelationshipsListRelationshipType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type ReportsListParams = {
date_from?: string;
date_to?: string;
is_private?: boolean;
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
person?: number;
/**
 * A search term.
 */
search?: string;
/**
 * * `firsthand` - Firsthand
* `secondhand` - Secondhand
* `news` - News report
* `document` - Document
 */
source_type?: ReportsListSourceType;
};

export type ReportsListSourceType = typeof ReportsListSourceType[keyof typeof ReportsListSourceType];

// eslint-disable-next-line @typescript-eslint/no-redeclare

export type TestimonialTagsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

export type TestimonialsListParams = {
/**
 * Which field to use when ordering the results.
 */
ordering?: string;
/**
 * A page number within the paginated result set.
 */
page?: number;
/**
 * A search term.
 */
search?: string;
};

