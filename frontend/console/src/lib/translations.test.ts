import { describe, expect, it } from "vitest";

import {
	translateActor,
	translateBlocker,
	translateExceptionReason,
	translateNextAction,
} from "./translations";

describe("console process translations", () => {
	it("translates job next actions by stable code", () => {
		expect(
			translateNextAction({
				code: "DISPATCH_JOB",
				message: "Assign or dispatch the service team",
			}),
		).toBe("إسناد فريق الخدمة أو توزيعه");
	});

	it("preserves dynamic blocker counts", () => {
		expect(
			translateBlocker({
				code: "ACTIVE_VISITS",
				message: "Complete or cancel 3 active service visit(s)",
			}),
		).toBe("أكمل أو ألغِ 3 زيارة خدمة نشطة");
	});

	it("translates server actors and exception reasons", () => {
		expect(translateActor("FSM Manager")).toBe("مدير الخدمة الميدانية");
		expect(translateExceptionReason("No service team is assigned")).toBe(
			"لم يتم إسناد فريق خدمة",
		);
	});
});
