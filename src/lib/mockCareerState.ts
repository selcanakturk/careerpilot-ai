export type MockCareerState = {
  hasUploadedCV: boolean;
  hasAnalysis: boolean;
  latestTargetRole: string;
  latestFileName: string;
  latestExperienceLevel: string;
};

const STORAGE_KEY = 'careerPilot.mockCareerState';

export const emptyMockCareerState: MockCareerState = {
  hasUploadedCV: false,
  hasAnalysis: false,
  latestTargetRole: '',
  latestFileName: '',
  latestExperienceLevel: '',
};

export function readMockCareerState(): MockCareerState {
  try {
    const storedValue = localStorage.getItem(STORAGE_KEY);

    if (!storedValue) {
      return emptyMockCareerState;
    }

    const parsedValue = JSON.parse(storedValue) as Partial<MockCareerState>;

    return {
      hasUploadedCV: parsedValue.hasUploadedCV === true,
      hasAnalysis: parsedValue.hasAnalysis === true,
      latestTargetRole:
        typeof parsedValue.latestTargetRole === 'string' ? parsedValue.latestTargetRole : '',
      latestFileName:
        typeof parsedValue.latestFileName === 'string' ? parsedValue.latestFileName : '',
      latestExperienceLevel:
        typeof parsedValue.latestExperienceLevel === 'string'
          ? parsedValue.latestExperienceLevel
          : '',
    };
  } catch {
    return emptyMockCareerState;
  }
}

export function writeMockCareerState(state: MockCareerState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clearMockCareerState() {
  localStorage.removeItem(STORAGE_KEY);
}
