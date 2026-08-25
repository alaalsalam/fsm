export { FrappeClient, createClient } from "./src/client";
export { Auth, type SessionUser } from "./src/auth";
export { Realtime, type RealtimeOptions } from "./src/socket";
export { FrappeError, type ClientOptions, type ListParams } from "./src/types";
export {
	InstalledBaseApi,
	type CustomerSiteSummary,
	type CustomerSiteDetail,
	type EquipmentLocation,
	type InstalledEquipmentSummary,
	type InstalledEquipmentDetail,
	type EquipmentHistoryEvent,
	type JobEquipmentRow,
	type EquipmentFilters,
	type EquipmentStatus,
	type WarrantyStatus,
} from "./src/installed-base";
export {
	ContractsApi,
	type ContractStatus,
	type CoverageStatus,
	type ContractSummary,
	type ContractCoverageRule,
	type ContractEntitlement,
	type ContractDetail,
	type CoverageDecision,
	type CreateContractInput,
} from "./src/contracts";
export {
	MaintenanceApi,
	type MaintenancePlanStatus,
	type MaintenanceOccurrenceStatus,
	type MaintenancePlanSummary,
	type MaintenanceOccurrence,
	type MaintenanceSummary,
	type CreateMaintenancePlanInput,
} from "./src/maintenance";
export {
	InspectionsApi,
	type InspectionResponseType,
	type InspectionOverallResult,
	type InspectionResultRow,
	type EquipmentInspection,
	type InspectionTemplateSummary,
	type InspectionResponseInput,
} from "./src/inspections";
export { FireSafetyApi, type FireExtinguisherProfileInput } from "./src/fire-safety";
export {
	MaterialsApi,
	type MaterialType,
	type MaterialAction,
	type MaterialInput,
	type MaterialPlanRow,
	type MaterialPlan,
} from "./src/materials";
export {
	FailureAnalysisApi,
	type FailureAnalysisStatus,
	type FailureSeverity,
	type FailureAnalysis,
} from "./src/failure-analysis";
export {
	WorkshopApi,
	type WorkshopStatus,
	type WorkshopOutcome,
	type WorkshopCase,
} from "./src/workshop";
