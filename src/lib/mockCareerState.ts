export type MockCareerState = {
  hasUploadedCV: boolean;
  hasAnalysis: boolean;
  latestTargetRole: string;
  latestFileName: string;
  latestExperienceLevel: string;
  storagePath: string;
  storageFullPath: string;
  storageBucket: string;
  storageSize: number;
  storageMimeType: string;
  cvUploadId: string;
  uploadedAt: string;
};

const STORAGE_KEY = 'careerPilot.mockCareerState';

export const emptyMockCareerState: MockCareerState = {
  hasUploadedCV: false,
  hasAnalysis: false,
  latestTargetRole: '',
  latestFileName: '',
  latestExperienceLevel: '',
  storagePath: '',
  storageFullPath: '',
  storageBucket: '',
  storageSize: 0,
  storageMimeType: '',
  cvUploadId: '',
  uploadedAt: '',
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
      storagePath: typeof parsedValue.storagePath === 'string' ? parsedValue.storagePath : '',
      storageFullPath:
        typeof parsedValue.storageFullPath === 'string' ? parsedValue.storageFullPath : '',
      storageBucket: typeof parsedValue.storageBucket === 'string' ? parsedValue.storageBucket : '',
      storageSize: typeof parsedValue.storageSize === 'number' ? parsedValue.storageSize : 0,
      storageMimeType:
        typeof parsedValue.storageMimeType === 'string' ? parsedValue.storageMimeType : '',
      cvUploadId: typeof parsedValue.cvUploadId === 'string' ? parsedValue.cvUploadId : '',
      uploadedAt: typeof parsedValue.uploadedAt === 'string' ? parsedValue.uploadedAt : '',
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
